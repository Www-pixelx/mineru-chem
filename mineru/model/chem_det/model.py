import os
from typing import List, Union
from tqdm import tqdm
from ultralytics import YOLO
import numpy as np
from PIL import Image, ImageDraw


class ChemDetModel:
    def __init__(
        self,
        weight: str,
        device: str = "cpu",
        imgsz: int = 1888,
        conf: float = 0.7,
        iou: float = 0.45,
    ):
        self.model = YOLO(weight).to(device)
        self.device = device
        self.imgsz = imgsz
        self.conf = conf
        self.iou = iou

    def _run_predict(
        self,
        inputs: Union[np.ndarray, Image.Image, List],
        is_batch: bool = False
    ) -> List:
        preds = self.model.predict(
            inputs,
            imgsz=self.imgsz,
            conf=self.conf,
            iou=self.iou,
            verbose=False,
            device=self.device
        )
        return [pred.cpu() for pred in preds] if is_batch else preds[0].cpu()

    def predict(self, image: Union[np.ndarray, Image.Image]):
        return self._run_predict(image)

    def batch_predict(
        self,
        images: List[Union[np.ndarray, Image.Image]],
        batch_size: int = 4
    ) -> List:
        results = []
        with tqdm(total=len(images), desc="ChemDet Predict") as pbar:
            for idx in range(0, len(images), batch_size):
                batch = images[idx: idx + batch_size]
                batch_preds = self._run_predict(batch, is_batch=True)
                results.extend(batch_preds)
                pbar.update(len(batch))
        return results

    def visualize(
        self,
        image: Union[np.ndarray, Image.Image],
        results: List
    ) -> Image.Image:

        if isinstance(image, np.ndarray):
            image = Image.fromarray(image)

        formula_list = []
        for xyxy, conf in zip(
                results.boxes.xyxy.cpu(), results.boxes.conf.cpu()
                ):
            xmin, ymin, xmax, ymax = [int(p.item()) for p in xyxy]
            new_item = {
                "category_id": 16,
                "poly": [xmin, ymin, xmax, ymin, xmax, ymax, xmin, ymax],
                "score": round(float(conf.item()), 2),
            }
            formula_list.append(new_item)

        draw = ImageDraw.Draw(image)
        for res in formula_list:
            poly = res['poly']
            xmin, ymin, xmax, ymax = poly[0], poly[1], poly[4], poly[5]
            print(
                f"Detected box: {xmin}, {ymin}, {xmax}, {ymax}, Category ID: {res['category_id']}, Score: {res['score']}")
            # 使用PIL在图像上画框
            draw.rectangle([xmin, ymin, xmax, ymax], outline="red", width=2)
            # 在框旁边画置信度
            draw.text((xmax + 10, ymin + 10), f"{res['score']:.2f}", fill="red", font_size=22)
        return image

if __name__ == '__main__':
    image_path = '/data/wyn/projects/pic.png'
    weights = '/data/wyn/projects/Patent-Classification-Platform-main/assets/best.pt'
    device = 'cuda'
    model = ChemDetModel(
        weight=weights,
        device=device,
    )
    image = Image.open(image_path)
    results = model.predict(image)

    print("Detection Results:")
    print(results)
    image = model.visualize(image, results)

    output_path = os.path.join(os.path.dirname(image_path), "chem_det_vis.png")
    image.save(output_path)
    print(f"Visualization saved to {output_path}")