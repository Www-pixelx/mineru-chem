# MinerU Pipeline 流程（函数级，输入到输出）

> 说明：本文只描述 MinerU 仓库内的 pipeline 后端流程（非 VLM / hybrid）。入口以 CLI 的 `do_parse()` 为主，按真实调用链展开。

---

## 1. 总览（输入 → 输出）

**输入**：PDF / 图片文件的字节流（`pdf_bytes_list`）与文件名列表（`pdf_file_names`）、语言列表（`p_lang_list`）。

**核心产物**：
- `middle_json`（中间结构化 JSON）
- `pdf_info`（页面级结构与内容块）
- Markdown（可选）
- content_list（可选）
- 原始 PDF（可选）
- 模型输出 JSON（可选）

**输出路径**：
```
output_dir/
  <pdf_name>/
    <parse_method>/
      <pdf_name>.md
      <pdf_name>_content_list.json
      <pdf_name>_middle.json
      <pdf_name>_model.json
      <pdf_name>_origin.pdf
      images/
        ...
```

---

## 2. 入口与调度（CLI 层）

### 2.1 `do_parse()` — 解析总入口
- 位置：mineru/cli/common.py
- 作用：
  1. 调整/截取页码范围（`_prepare_pdf_bytes()`）
  2. 选择 backend：当 `backend == "pipeline"` 走 pipeline；否则进入 VLM 分支

关键调用链：
```
read_fn() 读取文件字节
 → do_parse()
   → _prepare_pdf_bytes()
   → _process_pipeline()
```

### 2.2 `_prepare_pdf_bytes()` — 页码裁剪
- 位置：mineru/cli/common.py
- 作用：调用 `convert_pdf_bytes_to_bytes_by_pypdfium2()` 截取 PDF 页码范围。

---

## 3. Pipeline 主流程（模型推理 → middle_json）

### 3.1 `_process_pipeline()` — Pipeline 调度
- 位置：mineru/cli/common.py
- 作用：
  1. 调用 `pipeline_doc_analyze()` 得到模型原始推理结果
  2. 调用 `result_to_middle_json()` 生成结构化 middle_json
  3. 调用 `_process_output()` 生成最终文件

关键调用链：
```
_process_pipeline()
  → pipeline_doc_analyze()  # mineru/backend/pipeline/pipeline_analyze.py
  → pipeline_result_to_middle_json()  # mineru/backend/pipeline/model_json_to_middle_json.py
  → _process_output()
```

### 3.2 `doc_analyze()` — 批量页面推理
- 位置：mineru/backend/pipeline/pipeline_analyze.py
- 作用：
  1. 判断是否需要 OCR（`parse_method` + `classify()`）
  2. `load_images_from_pdf()` 把 PDF 转成多页 PIL 图像
  3. 统一组装页面任务：`images_with_extra_info` = (img, ocr_enable, lang)
  4. 分批处理：`batch_image_analyze()`
  5. 汇总为 `infer_results`（按 PDF & 页码组织）

关键点：
- `MINERU_MIN_BATCH_INFERENCE_SIZE` 控制 batch 大小（默认 384）。
- `ocr_enabled_list` 记录每个 PDF 是否启用 OCR。

### 3.3 `batch_image_analyze()` — 批量模型调用入口
- 位置：mineru/backend/pipeline/pipeline_analyze.py
- 作用：
  1. 选择 device 并估算 VRAM
  2. 依据 VRAM 计算 `batch_ratio`
  3. 选择是否启用 OCR det 批处理（torch 版本或 mps 限制）
  4. 构建 `BatchAnalyze` 并执行

### 3.4 `BatchAnalyze.__call__()` — 核心推理流程
- 位置：mineru/backend/pipeline/batch_analyze.py
- 作用：对每一页图像完成布局检测、公式检测/识别、OCR 识别、表格结构化。

主要步骤（按顺序）：
1. **布局检测**：`layout_model.batch_predict()`（doclayout_yolo）
2. **公式检测与识别**（可选）：
   - `mfd_model.batch_predict()`
   - `mfr_model.batch_predict()`
3. **生成 OCR / 表格候选**：`get_res_list_from_layout_res()`
4. **表格识别**（可选）：
   - 方向分类 `ImgOrientationCls`
   - 表格类型分类 `TableCls`
   - OCR det + rec（按语言分组）
   - 无线/有线表格模型处理
5. **OCR det**（两种模式）：
   - 批处理模式：按语言与分辨率分组
   - 单张模式：逐块裁剪识别
6. **OCR rec**：对 text span 进行识别并回填内容与置信度

最终输出：每页 layout + OCR + 表格 + 公式等合并后的结构化结果列表。

---

## 4. Model JSON → middle_json

### 4.1 `result_to_middle_json()` — 构建中间结构
- 位置：mineru/backend/pipeline/model_json_to_middle_json.py
- 作用：把模型输出转成统一的 `middle_json`，并包含 `pdf_info`。

核心步骤：
1. 逐页调用 `page_model_info_to_page_info()` 生成页面级结构
2. 后置 OCR：对需要 OCR 的 spans 再补一次识别
3. 分段：`para_split()`
4. 表格跨页合并：`merge_table()`
5. LLM 辅助标题优化（可选）：`llm_aided_title()`

### 4.2 `page_model_info_to_page_info()` — 页面结构化
- 位置：mineru/backend/pipeline/model_json_to_middle_json.py
- 作用：把单页模型输出转为结构化 blocks + spans。

关键处理：
- `MagicModel` 提取 block / span
- 过滤水印、重复 span、低置信度 span
- 识别图、表、公式，生成裁剪文件
- span 填充到 block，再排序
- 生成 `page_info`（包含 `preproc_blocks`、`discarded_blocks`）

输出结构示意：
```
page_info = {
  "preproc_blocks": [...],
  "discarded_blocks": [...],
  "page_idx": <int>,
  "page_size": [w, h]
}
```

---

## 5. middle_json → 文件输出

### 5.1 `_process_output()` — 统一落盘
- 位置：mineru/cli/common.py
- 作用：根据开关输出各种文件。

输出项：
- 版面标注 PDF（可选）：`draw_layout_bbox()` / `draw_span_bbox()`
- 原始 PDF（可选）
- Markdown（可选）：`pipeline_middle_json_mkcontent.union_make()`
- content_list（可选）：`pipeline_middle_json_mkcontent.union_make()`
- middle_json / model_json（可选）

### 5.2 `pipeline_middle_json_mkcontent.union_make()` — 生成 Markdown / content_list
- 位置：mineru/backend/pipeline/pipeline_middle_json_mkcontent.py
- 作用：把 `pdf_info` 中的 `para_blocks` 按 `MakeMode` 生成：
  - `MakeMode.MM_MD`：多模态 Markdown
  - `MakeMode.NLP_MD`：纯文本 Markdown
  - `MakeMode.CONTENT_LIST`：结构化列表

---

## 6. 关键配置与影响点（便于理解）

- `parse_method`：
  - `auto`：通过 `classify()` 自动决定是否 OCR
  - `ocr`：强制 OCR
- `formula_enable` / `table_enable`：控制公式和表格模块是否启用
- `MINERU_MIN_BATCH_INFERENCE_SIZE`：影响 batch 大小
- `MINERU_VIRTUAL_VRAM_SIZE`：影响 `batch_ratio`

---

## 7. 调用链速查（函数级）

```
read_fn()
  → do_parse()
    → _prepare_pdf_bytes()
    → _process_pipeline()
      → pipeline_doc_analyze()
        → doc_analyze()
          → classify()
          → load_images_from_pdf()
          → batch_image_analyze()
            → BatchAnalyze.__call__()
              → layout_model.batch_predict()
              → mfd_model.batch_predict()
              → mfr_model.batch_predict()
              → OCR det/rec + table models
        → result_to_middle_json()
          → page_model_info_to_page_info()
          → para_split()
          → merge_table()
          → llm_aided_title()
      → _process_output()
        → pipeline_middle_json_mkcontent.union_make()
```

---

## 8. 你可以从哪里开始读

如果只看三处，建议：
1. mineru/cli/common.py（调度与输出）
2. mineru/backend/pipeline/pipeline_analyze.py（批量推理入口）
3. mineru/backend/pipeline/model_json_to_middle_json.py（结构化结果与后处理）
