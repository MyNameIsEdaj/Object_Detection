"""ONNX Runtime wrapper for YOLO models exported by Ultralytics (YOLOv8 / YOLO11).

Handles everything between "a BGR webcam frame" and "a list of boxes":
model loading (GPU via DirectML when available), letterbox preprocessing that
matches how Ultralytics trains, vectorised decoding and NMS.
"""
import ast
from dataclasses import dataclass

import cv2
import numpy as np
import onnxruntime as ort

GPU_PROVIDERS = ("DmlExecutionProvider", "CUDAExecutionProvider")


@dataclass
class Detection:
    box: tuple  # (x, y, w, h) in original-frame pixels
    conf: float
    cls_id: int
    label: str


class YoloOnnxDetector:
    def __init__(self, model_path, conf_threshold=0.25, iou_threshold=0.45,
                 prefer_gpu=True, agnostic_nms=True):
        """
        agnostic_nms=True: overlapping boxes of *different* classes also suppress
        each other, so one object never gets two labels. Set False to allow
        overlapping objects of different classes (e.g. a watch next to a can).
        """
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.agnostic_nms = agnostic_nms

        available = ort.get_available_providers()
        wanted = (list(GPU_PROVIDERS) if prefer_gpu else []) + ["CPUExecutionProvider"]
        providers = [p for p in wanted if p in available]
        self.session = ort.InferenceSession(str(model_path), providers=providers)
        self.provider = self.session.get_providers()[0]

        inp = self.session.get_inputs()[0]
        self.input_name = inp.name
        meta = self.session.get_modelmeta().custom_metadata_map
        self.input_h, self.input_w = self._read_input_size(inp.shape, meta)
        self.class_names = self._read_class_names(meta)

    # ------------------------------------------------------------------ info
    @property
    def uses_gpu(self):
        return self.provider != "CPUExecutionProvider"

    @property
    def device_label(self):
        return {"DmlExecutionProvider": "GPU (DirectML)",
                "CUDAExecutionProvider": "GPU (CUDA)"}.get(self.provider, "CPU")

    # ------------------------------------------------------------ inference
    def detect(self, frame, conf_threshold=None):
        """Run the model on one BGR frame and return a list of Detection.

        conf_threshold overrides self.conf_threshold for this call (the tracker
        asks for weaker detections too, to keep following blurred objects).
        """
        tensor, ratio, pad = self._letterbox(frame)
        output = self.session.run(None, {self.input_name: tensor})[0]
        thr = self.conf_threshold if conf_threshold is None else conf_threshold
        return self._postprocess(output, ratio, pad, frame.shape[:2], thr)

    def _letterbox(self, frame):
        """Resize keeping aspect ratio, pad to the model size with grey (114).

        The old code stretched the frame straight to 640x640, which distorts
        objects compared to what the model saw during training.
        """
        h, w = frame.shape[:2]
        ratio = min(self.input_w / w, self.input_h / h)
        new_w, new_h = int(round(w * ratio)), int(round(h * ratio))
        pad_w, pad_h = (self.input_w - new_w) / 2, (self.input_h - new_h) / 2
        left, top = int(round(pad_w - 0.1)), int(round(pad_h - 0.1))
        right, bottom = int(round(pad_w + 0.1)), int(round(pad_h + 0.1))

        img = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        img = cv2.copyMakeBorder(img, top, bottom, left, right,
                                 cv2.BORDER_CONSTANT, value=(114, 114, 114))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        tensor = img.transpose(2, 0, 1)[np.newaxis].astype(np.float32) / 255.0
        return np.ascontiguousarray(tensor), ratio, (left, top)

    def _postprocess(self, output, ratio, pad, frame_hw, conf_threshold):
        preds = output[0].T  # (num_anchors, 4 + num_classes)
        scores_all = preds[:, 4:]
        cls_ids = scores_all.argmax(axis=1)
        scores = scores_all[np.arange(len(preds)), cls_ids]

        keep = scores > conf_threshold
        if not keep.any():
            return []
        preds, cls_ids, scores = preds[keep], cls_ids[keep], scores[keep]

        # cx, cy, w, h (model space) -> x, y, w, h (original frame)
        frame_h, frame_w = frame_hw
        x1 = (preds[:, 0] - preds[:, 2] / 2 - pad[0]) / ratio
        y1 = (preds[:, 1] - preds[:, 3] / 2 - pad[1]) / ratio
        x2 = (preds[:, 0] + preds[:, 2] / 2 - pad[0]) / ratio
        y2 = (preds[:, 1] + preds[:, 3] / 2 - pad[1]) / ratio
        x1, x2 = np.clip(x1, 0, frame_w), np.clip(x2, 0, frame_w)
        y1, y2 = np.clip(y1, 0, frame_h), np.clip(y2, 0, frame_h)
        boxes = np.stack([x1, y1, x2 - x1, y2 - y1], axis=1)

        box_list, score_list = boxes.tolist(), scores.astype(float).tolist()
        if self.agnostic_nms:
            idx = cv2.dnn.NMSBoxes(box_list, score_list,
                                   conf_threshold, self.iou_threshold)
        else:
            idx = cv2.dnn.NMSBoxesBatched(box_list, score_list, cls_ids.tolist(),
                                          conf_threshold, self.iou_threshold)

        detections = []
        for i in np.array(idx).flatten():
            x, y, w, h = (int(round(v)) for v in boxes[i])
            cid = int(cls_ids[i])
            detections.append(Detection((x, y, w, h), float(scores[i]), cid,
                                        self.label_for(cid)))
        return detections

    def label_for(self, cls_id):
        if 0 <= cls_id < len(self.class_names):
            return self.class_names[cls_id]
        return f"class {cls_id}"

    # ------------------------------------------------------------- metadata
    @staticmethod
    def _read_input_size(shape, meta):
        h, w = shape[2], shape[3]
        if isinstance(h, int) and isinstance(w, int):
            return h, w
        try:  # dynamic export: fall back to the size stored by Ultralytics
            size = ast.literal_eval(meta.get("imgsz", "[640, 640]"))
            return int(size[0]), int(size[1])
        except (ValueError, SyntaxError):
            return 640, 640

    def _read_class_names(self, meta):
        """Ultralytics stores names as "{0: 'can', 1: 'glasses', ...}"."""
        try:
            names = ast.literal_eval(meta.get("names", "{}"))
            if isinstance(names, dict) and names:
                return [str(names[i]) for i in sorted(names)]
        except (ValueError, SyntaxError):
            pass
        n_out = self.session.get_outputs()[0].shape[1]
        n_classes = n_out - 4 if isinstance(n_out, int) else 0
        return [f"class {i}" for i in range(n_classes)]
