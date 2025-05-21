import os
import shutil
import zipfile
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any
import uuid
import threading
import time

app = FastAPI(title="MinerU PDF 批量解析API", description="基于magic-pdf的批量PDF解析与下载API，自动生成Swagger文档。", version="1.0.0")

# 允许局域网跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
PARSED_DIR = "parsed_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PARSED_DIR, exist_ok=True)

# 批量上传PDF文件
def save_upload_files(files: List[UploadFile], upload_dir: str):
    saved_paths = []
    original_name_map = {}
    for file in files:
        filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join(upload_dir, filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        saved_paths.append(file_path)
        # 记录原始文件名
        original_name_map[file_path] = file.filename
    return saved_paths, original_name_map

# 调用magic-pdf命令行解析
import subprocess

import shutil

import glob

def parse_pdf_files(pdf_paths: List[str], output_dir: str, original_name_map=None):
    parsed_files = []
    for pdf_path in pdf_paths:
        # 获取原始文件名（无uuid）
        if original_name_map and pdf_path in original_name_map:
            orig_filename = original_name_map[pdf_path]
        else:
            orig_filename = os.path.basename(pdf_path)
        base_name = os.path.splitext(orig_filename)[0]
        # 复制一份临时无uuid文件用于解析
        tmp_pdf_path = os.path.join(os.path.dirname(pdf_path), orig_filename)
        shutil.copy(pdf_path, tmp_pdf_path)
        # magic-pdf输出到临时目录
        tmp_out_dir = os.path.join(output_dir, f"{base_name}_tmpout")
        os.makedirs(tmp_out_dir, exist_ok=True)
        try:
            subprocess.run([
                "magic-pdf", "-p", tmp_pdf_path, "-o", tmp_out_dir
            ], check=True)
            # 查找magic-pdf输出的主目录（通常为 tmp_out_dir/base_name）
            subdirs = [d for d in os.listdir(tmp_out_dir) if os.path.isdir(os.path.join(tmp_out_dir, d))]
            if subdirs and base_name in subdirs:
                magic_pdf_dir = os.path.join(tmp_out_dir, base_name)
            else:
                # fallback: 只有一个子目录时也兼容
                magic_pdf_dir = os.path.join(tmp_out_dir, subdirs[0]) if subdirs else tmp_out_dir
            # 移动整个magic-pdf输出目录到parsed_files下
            final_dir = os.path.join(output_dir, base_name)
            if os.path.exists(final_dir):
                shutil.rmtree(final_dir)
            shutil.move(magic_pdf_dir, final_dir)
            # 查找主md文件，供前端展示
            md_candidates = glob.glob(os.path.join(final_dir, "**", "*.md"), recursive=True)
            if md_candidates:
                parsed_files.extend(md_candidates)
            shutil.rmtree(tmp_out_dir)
        except Exception as e:
            print(f"解析失败: {pdf_path}, 错误: {e}")
        finally:
            if os.path.exists(tmp_pdf_path):
                os.remove(tmp_pdf_path)
    return parsed_files

# ------------------- 异步解析与进度管理 -------------------
parse_tasks: Dict[str, Dict[str, Any]] = {}
# 结构: {task_id: {"files": [{"filename": str, "status": "pending|parsing|success|failed", "progress": int}], "overall": int, "done": bool}}

def async_parse_worker(task_id: str, filenames: List[str]):
    parse_tasks[task_id] = {"files": [], "overall": 0, "done": False}
    total = len(filenames)
    for idx, fname in enumerate(filenames):
        file_status = {"filename": fname, "status": "parsing", "progress": 0}
        parse_tasks[task_id]["files"].append(file_status)
        pdf_path = os.path.join(UPLOAD_DIR, fname)
        orig_filename = fname.split('_', 1)[-1] if '_' in fname else fname
        base_name = os.path.splitext(orig_filename)[0]
        tmp_pdf_path = os.path.join(UPLOAD_DIR, orig_filename)
        shutil.copy(pdf_path, tmp_pdf_path)
        tmp_out_dir = os.path.join(PARSED_DIR, f"{base_name}_tmpout")
        os.makedirs(tmp_out_dir, exist_ok=True)
        try:
            subprocess.run([
                "magic-pdf", "-p", tmp_pdf_path, "-o", tmp_out_dir
            ], check=True)
            subdirs = [d for d in os.listdir(tmp_out_dir) if os.path.isdir(os.path.join(tmp_out_dir, d))]
            if subdirs and base_name in subdirs:
                magic_pdf_dir = os.path.join(tmp_out_dir, base_name)
            else:
                magic_pdf_dir = os.path.join(tmp_out_dir, subdirs[0]) if subdirs else tmp_out_dir
            final_dir = os.path.join(PARSED_DIR, base_name)
            if os.path.exists(final_dir):
                shutil.rmtree(final_dir)
            shutil.move(magic_pdf_dir, final_dir)
            md_candidates = glob.glob(os.path.join(final_dir, "**", "*.md"), recursive=True)
            if md_candidates:
                file_status["status"] = "success"
                file_status["progress"] = 100
            else:
                file_status["status"] = "failed"
                file_status["progress"] = 0
            shutil.rmtree(tmp_out_dir)
        except Exception as e:
            file_status["status"] = "failed"
            file_status["progress"] = 0
        finally:
            if os.path.exists(tmp_pdf_path):
                os.remove(tmp_pdf_path)
        parse_tasks[task_id]["overall"] = int((idx + 1) / total * 100)
    parse_tasks[task_id]["done"] = True

@app.post("/upload", summary="批量上传PDF文件")
async def upload_files(files: List[UploadFile] = File(...)):
    saved_paths, original_name_map = save_upload_files(files, UPLOAD_DIR)
    return {"uploaded_files": [os.path.basename(p) for p in saved_paths]}

@app.post("/parse", summary="批量解析PDF为Markdown")
async def parse_files(background_tasks: BackgroundTasks, filenames: List[str]):
    pdf_paths = [os.path.join(UPLOAD_DIR, name) for name in filenames]
    parsed_paths = parse_pdf_files(pdf_paths, PARSED_DIR)
    return {"parsed_files": [os.path.basename(p) for p in parsed_paths]}

@app.get("/download", summary="批量下载解析后的文件")
def download_parsed_files():
    zip_path = os.path.join(PARSED_DIR, "parsed_files.zip")
    with zipfile.ZipFile(zip_path, "w") as zipf:
        # 遍历parsed_files下所有.md文件，打包其所在目录全部内容
        for root, _, files in os.walk(PARSED_DIR):
            for file in files:
                if file.endswith(".md"):
                    abs_md = os.path.join(root, file)
                    # 获取md文件所在的根目录（如 base_name）
                    rel_md = os.path.relpath(abs_md, PARSED_DIR)
                    parts = rel_md.split(os.sep)
                    if len(parts) > 1:
                        root_dir = os.path.join(PARSED_DIR, parts[0])
                    else:
                        root_dir = os.path.dirname(abs_md)
                    # 将该根目录下所有内容都打包
                    for folder, _, subfiles in os.walk(root_dir):
                        for subfile in subfiles:
                            abs_file = os.path.join(folder, subfile)
                            rel_file = os.path.relpath(abs_file, PARSED_DIR)
                            zipf.write(abs_file, arcname=rel_file)
    return FileResponse(zip_path, filename="parsed_files.zip", media_type="application/zip")

from fastapi import Query, Body
from typing import Optional
from fastapi.responses import StreamingResponse

# 列出所有已上传PDF文件
@app.get("/list_uploaded_files", summary="列出所有上传的PDF文件")
def list_uploaded_files():
    files = []
    for fname in os.listdir(UPLOAD_DIR):
        if fname.lower().endswith('.pdf'):
            abs_path = os.path.join(UPLOAD_DIR, fname)
            files.append({
                "name": fname,
                "size": os.path.getsize(abs_path),
                "mtime": os.path.getmtime(abs_path)
            })
    return {"files": sorted(files, key=lambda x: x["mtime"], reverse=True)}

# 删除上传的PDF文件
from pydantic import BaseModel
from typing import List

class FilenamesModel(BaseModel):
    filenames: List[str]

@app.post("/delete_uploaded_file", summary="批量删除上传的PDF文件")
def delete_uploaded_file(data: FilenamesModel):
    filenames = data.filenames
    results = []
    for filename in filenames:
        abs_path = os.path.join(UPLOAD_DIR, filename)
        if os.path.exists(abs_path):
            try:
                os.remove(abs_path)
                results.append({"filename": filename, "success": True})
            except PermissionError as e:
                results.append({"filename": filename, "success": False, "error": f"Permission denied: {str(e)}"})
            except Exception as e:
                results.append({"filename": filename, "success": False, "error": f"Delete failed: {str(e)}"})
        else:
            results.append({"filename": filename, "success": False, "error": "File not found"})
    return {"results": results}



# 批量下载上传的PDF文件为zip
@app.post("/download_uploaded_files", summary="批量下载上传的PDF文件为zip")
def download_uploaded_files(filenames: list = Body(...)):
    zip_path = os.path.join(UPLOAD_DIR, "uploaded_files.zip")
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for filename in filenames:
            abs_path = os.path.join(UPLOAD_DIR, filename)
            if os.path.exists(abs_path):
                zipf.write(abs_path, arcname=filename)
    return FileResponse(zip_path, filename="uploaded_files.zip", media_type="application/zip")


# 下载上传的PDF文件
@app.get("/download_uploaded_file", summary="下载上传的PDF文件")
def download_uploaded_file(filename: str):
    abs_path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(abs_path):
        return FileResponse(abs_path, filename=filename, media_type="application/pdf")
    return JSONResponse({"error": "File not found"}, status_code=404)

# 递归列出所有md文件（含元数据）
@app.get("/list_md_files", summary="递归列出所有md文件")
def list_md_files():
    md_files = []
    for root, _, files in os.walk(PARSED_DIR):
        for file in files:
            if file.endswith(".md"):
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, PARSED_DIR)
                stat = os.stat(abs_path)
                md_files.append({
                    "path": rel_path,
                    "name": file,
                    "size": stat.st_size,
                    "mtime": stat.st_mtime
                })
    return {"files": sorted(md_files, key=lambda x: x["mtime"], reverse=True)}

class MdPathModel(BaseModel):
    md_path: str

class MdPathsListModel(BaseModel):
    md_paths: List[str]

# 删除md文件及其所在目录
@app.post("/delete_md_file", summary="删除解析后的md文件及其目录")
def delete_md_file(data: MdPathModel):
    md_path = data.md_path
    abs_md = os.path.join(PARSED_DIR, md_path)
    if os.path.exists(abs_md):
        # 获取根目录（如 base_name）
        parts = md_path.split(os.sep)
        if len(parts) > 1:
            root_dir = os.path.join(PARSED_DIR, parts[0])
        else:
            root_dir = os.path.dirname(abs_md)
        if os.path.exists(root_dir) and os.path.isdir(root_dir):
            try:
                shutil.rmtree(root_dir)
                return {"success": True}
            except Exception as e:
                return {"success": False, "error": str(e)}
    return {"success": False, "error": "File not found"}

# 批量删除md文件及其所在目录
@app.post("/batch_delete_md_files", summary="批量删除解析后的md文件及其目录")
def batch_delete_md_files(data: MdPathsListModel):
    results = []
    for md_path in data.md_paths:
        abs_md = os.path.join(PARSED_DIR, md_path)
        if os.path.exists(abs_md):
            # 获取根目录（如 base_name）
            parts = md_path.split(os.sep)
            if len(parts) > 1:
                root_dir = os.path.join(PARSED_DIR, parts[0])
            else:
                root_dir = os.path.dirname(abs_md)
            if os.path.exists(root_dir) and os.path.isdir(root_dir):
                try:
                    shutil.rmtree(root_dir)
                    results.append({"path": md_path, "success": True})
                except Exception as e:
                    results.append({"path": md_path, "success": False, "error": str(e)})
            else:
                results.append({"path": md_path, "success": False, "error": "Directory not found"})
        else:
            results.append({"path": md_path, "success": False, "error": "File not found"})
    return {"results": results}

# 预览md文件内容
@app.get("/preview_md_file", summary="预览md文件内容")
def preview_md_file(md_path: str):
    abs_md = os.path.join(PARSED_DIR, md_path)
    if os.path.exists(abs_md):
        with open(abs_md, "r", encoding="utf-8") as f:
            content = f.read()
        return {"content": content}
    return JSONResponse({"error": "File not found"}, status_code=404)

# 下载单个md文件及其目录为zip
@app.get("/download_md_file", summary="下载单个md文件及其目录为zip")
def download_md_file(md_path: str):
    abs_md = os.path.join(PARSED_DIR, md_path)
    if os.path.exists(abs_md):
        parts = md_path.split(os.sep)
        if len(parts) > 1:
            root_dir = os.path.join(PARSED_DIR, parts[0])
        else:
            root_dir = os.path.dirname(abs_md)
        zip_path = os.path.join(PARSED_DIR, "single_md_download.zip")
        with zipfile.ZipFile(zip_path, "w") as zipf:
            for folder, _, files in os.walk(root_dir):
                for file in files:
                    abs_file = os.path.join(folder, file)
                    rel_file = os.path.relpath(abs_file, PARSED_DIR)
                    zipf.write(abs_file, arcname=rel_file)
        return FileResponse(zip_path, filename="md_content.zip", media_type="application/zip")
    return JSONResponse({"error": "File not found"}, status_code=404)

class FilenamesListModel(BaseModel):
    filenames: List[str]

# 只批量下载 MD 文件
@app.post("/download_md_files_only", summary="只批量下载选中的 Markdown 文件（不包含目录内其他文件）")
async def download_md_files_only(data: FilenamesListModel):
    try:
        filenames = data.filenames
        if not filenames or len(filenames) == 0:
            return JSONResponse({"error": "No files selected"}, status_code=400)
            
        zip_path = os.path.join(PARSED_DIR, "md_files_only.zip")
        with zipfile.ZipFile(zip_path, "w") as zipf:
            for md_rel_path in filenames:
                md_abs_path = os.path.join(PARSED_DIR, md_rel_path)
                if os.path.exists(md_abs_path) and md_abs_path.endswith(".md"):
                    # 只添加 MD 文件本身，不包含目录内其他文件
                    zipf.write(md_abs_path, arcname=os.path.basename(md_rel_path))
        return FileResponse(zip_path, filename="markdown_files.zip", media_type="application/zip")
    except Exception as e:
        return JSONResponse({"error": f"Error processing download: {str(e)}"}, status_code=500)

# 选择性批量下载
@app.post("/download_selected", summary="选择性下载解析后的Markdown文件及其全部内容")
async def download_selected_parsed_files(data: FilenamesListModel):
    try:
        filenames = data.filenames
        if not filenames or len(filenames) == 0:
            return JSONResponse({"error": "No files selected"}, status_code=400)
            
        zip_path = os.path.join(PARSED_DIR, "selected_files.zip")
        with zipfile.ZipFile(zip_path, "w") as zipf:
            for md_rel_path in filenames:
                md_abs_path = os.path.join(PARSED_DIR, md_rel_path)
                if os.path.exists(md_abs_path):
                    parts = md_rel_path.split(os.sep)
                    if len(parts) > 1:
                        root_dir = os.path.join(PARSED_DIR, parts[0])
                    else:
                        root_dir = os.path.dirname(md_abs_path)
                    for folder, _, files in os.walk(root_dir):
                        for file in files:
                            abs_file = os.path.join(folder, file)
                            rel_file = os.path.relpath(abs_file, PARSED_DIR)
                            zipf.write(abs_file, arcname=rel_file)
        return FileResponse(zip_path, filename="selected_files.zip", media_type="application/zip")
    except Exception as e:
        return JSONResponse({"error": f"Error processing download: {str(e)}"}, status_code=500)

@app.get("/health", summary="健康检查")
def health_check():
    return {"status": "ok"}

# ------------------- 新增异步解析与进度接口 -------------------
from fastapi import Body

@app.post("/parse_async", summary="异步批量解析PDF文件")
async def parse_files_async(data: FilenamesModel):
    filenames = data.filenames
    valid_filenames = []
    errors = []
    for fname in filenames:
        abs_path = os.path.join(UPLOAD_DIR, fname)
        if os.path.exists(abs_path):
            # 检查权限
            try:
                with open(abs_path, 'rb') as f:
                    pass
                valid_filenames.append(fname)
            except PermissionError as e:
                errors.append({"filename": fname, "error": f"Permission denied: {str(e)}"})
            except Exception as e:
                errors.append({"filename": fname, "error": f"Open failed: {str(e)}"})
        else:
            errors.append({"filename": fname, "error": "File not found"})
    if not valid_filenames:
        return JSONResponse({"error": "No valid files to parse", "details": errors}, status_code=400)
    task_id = str(uuid.uuid4())
    thread = threading.Thread(target=async_parse_worker, args=(task_id, valid_filenames))
    thread.start()
    return {"task_id": task_id, "errors": errors}

@app.get("/progress", summary="查询解析进度")
def get_progress(task_id: str):
    task = parse_tasks.get(task_id)
    if not task:
        return JSONResponse({"error": "无效的task_id"}, status_code=404)
    return task
