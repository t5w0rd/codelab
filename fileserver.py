import http.server
import socketserver
import os
import urllib.parse
import re
import socket

# 设置服务器端口
PORT = 8000

class SimpleFileServer(http.server.SimpleHTTPRequestHandler):
    
    def generate_unique_filename(self, filename, directory="."):
        """生成唯一的文件名，避免覆盖现有文件"""
        filepath = os.path.join(directory, filename)
        if not os.path.exists(filepath):
            return filename
        
        # 分离文件名和扩展名
        name, ext = os.path.splitext(filename)
        
        # 查找是否已有带编号的版本
        counter = 1
        pattern = re.compile(re.escape(name) + r' \((\d+)\)' + re.escape(ext) + r'$')
        
        # 查找现有的编号
        existing_counters = []
        for f in os.listdir(directory):
            if os.path.isfile(os.path.join(directory, f)):
                match = pattern.match(f)
                if match:
                    existing_counters.append(int(match.group(1)))
        
        # 确定下一个可用的编号
        if existing_counters:
            counter = max(existing_counters) + 1
        else:
            counter = 1
        
        # 生成新文件名
        new_filename = f"{name} ({counter}){ext}"
        
        # 递归检查，确保新文件名也不存在
        return self.generate_unique_filename(new_filename, directory)
    
    def is_safe_path(self, path):
        """检查路径是否安全，防止目录遍历攻击"""
        # 获取规范化的绝对路径
        root = os.path.abspath(".")
        requested_path = os.path.abspath(os.path.join(root, path.lstrip("/")))
        
        # 确保请求的路径在根目录内
        return requested_path.startswith(root)
    
    def list_directory(self, path):
        """生成目录列表页面"""
        try:
            # 安全检查
            if not self.is_safe_path(path):
                self.send_error(403, "禁止访问此目录")
                return None
            
            # 获取目录中的文件和子目录
            items = []
            for name in os.listdir(path):
                full_path = os.path.join(path, name)
                if os.path.isdir(full_path):
                    items.append(('dir', name))
                else:
                    items.append(('file', name))
            
            # 排序：目录在前，文件在后
            items.sort(key=lambda x: (x[0] != 'dir', x[1].lower()))
            
            # 生成目录列表HTML
            dir_list = []
            current_dir = path if path != "." else ""
            
            # 添加上级目录链接（如果不是根目录）
            if path != ".":
                parent_dir = os.path.dirname(path)
                if parent_dir == "":
                    parent_dir = "."
                dir_list.append(f'<li><a href="/browse/{parent_dir}">[上级目录]</a></li>')
            
            for item_type, name in items:
                if item_type == 'dir':
                    # 目录链接
                    dir_path = os.path.join(current_dir, name)
                    dir_list.append(f'<li>📁 <a href="/browse/{dir_path}">{self.escape_html(name)}/</a></li>')
                else:
                    # 文件下载链接
                    file_path = os.path.join(current_dir, name)
                    dir_list.append(f'<li>📄 <a href="/download/{urllib.parse.quote(file_path)}">{self.escape_html(name)}</a></li>')
            
            return ''.join(dir_list)
        except PermissionError:
            self.send_error(403, "没有权限访问此目录")
            return None
        except FileNotFoundError:
            self.send_error(404, "目录不存在")
            return None
    
    def do_GET(self):
        # 解析请求路径
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        
        # 处理目录浏览请求
        if path.startswith('/browse/'):
            dir_path = path[8:]  # 移除 '/browse/' 前缀
            if dir_path == "":
                dir_path = "."
            
            dir_list = self.list_directory(dir_path)
            if dir_list is None:
                return  # 错误已经在list_directory中处理
            
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            
            html = f"""
            <html>
            <head>
                <title>文件服务器 - {dir_path}</title>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; }}
                    ul {{ list-style-type: none; padding: 0; }}
                    li {{ padding: 5px 0; }}
                    a {{ text-decoration: none; color: #0366d6; }}
                    a:hover {{ text-decoration: underline; }}
                    form {{ margin: 20px 0; }}
                    .current-dir {{ background-color: #f0f0f0; padding: 10px; border-radius: 5px; }}
                </style>
            </head>
            <body>
                <h1>文件服务器</h1>
                <div class="current-dir">当前目录: {self.escape_html(dir_path)}</div>
                <h2>上传文件</h2>
                <form action="/upload/{dir_path}" method="post" enctype="multipart/form-data">
                    <input type="file" name="file">
                    <input type="submit" value="上传">
                </form>
                <h2>目录内容</h2>
                <ul>{dir_list}</ul>
                <p><a href="/">返回首页</a></p>
            </body>
            </html>
            """
            self.wfile.write(html.encode('utf-8'))
        
        # 处理下载请求
        elif path.startswith('/download/'):
            # 对URL编码的文件名进行解码
            filepath_encoded = path[10:]  # 移除 '/download/' 前缀
            filepath = urllib.parse.unquote(filepath_encoded)
            
            # 安全检查
            if not self.is_safe_path(filepath):
                self.send_error(403, "禁止访问此文件")
                return
            
            if os.path.exists(filepath) and os.path.isfile(filepath):
                self.send_response(200)
                self.send_header('Content-Type', 'application/octet-stream')
                
                # 获取文件名用于下载
                filename = os.path.basename(filepath)
                filename_header = filename.encode('utf-8').decode('latin-1')
                self.send_header('Content-Disposition', 
                                f"attachment; filename*=UTF-8''{urllib.parse.quote(filename)}; filename=\"{filename_header}\"")
                self.end_headers()
                
                with open(filepath, 'rb') as file:
                    self.wfile.write(file.read())
            else:
                self.send_error(404, f"文件不存在: {filepath}")
        
        # 首页
        else:
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            
            # 显示根目录下的内容
            dir_list = self.list_directory(".")
            if dir_list is None:
                return
            
            html = f"""
            <html>
            <head>
                <title>简单文件服务器</title>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; }}
                    ul {{ list-style-type: none; padding: 0; }}
                    li {{ padding: 5px 0; }}
                    a {{ text-decoration: none; color: #0366d6; }}
                    a:hover {{ text-decoration: underline; }}
                    form {{ margin: 20px 0; }}
                </style>
            </head>
            <body>
                <h1>简单文件服务器</h1>
                <h2>上传文件</h2>
                <form action="/upload/." method="post" enctype="multipart/form-data">
                    <input type="file" name="file">
                    <input type="submit" value="上传">
                </form>
                <h2>目录内容</h2>
                <ul>{dir_list}</ul>
            </body>
            </html>
            """
            self.wfile.write(html.encode('utf-8'))
    
    def do_POST(self):
        # 处理上传请求
        if self.path.startswith('/upload/'):
            try:
                upload_dir = self.path[8:]  # 移除 '/upload/' 前缀
                if upload_dir == "":
                    upload_dir = "."
                
                # 安全检查
                if not self.is_safe_path(upload_dir):
                    self.send_error(403, "禁止上传到此目录")
                    return
                
                # 获取内容类型和内容长度
                content_type = self.headers['Content-Type']
                content_length = int(self.headers['Content-Length'])
                
                if not content_type.startswith('multipart/form-data'):
                    self.send_error(400, "无效的内容类型")
                    return
                
                # 读取POST数据
                post_data = self.rfile.read(content_length)
                
                # 解析multipart数据
                boundary = content_type.split('boundary=')[1].encode()
                parts = post_data.split(b'--' + boundary)
                
                for part in parts:
                    if b'filename="' in part:
                        # 提取文件名 - 处理中文文件名
                        filename_start = part.find(b'filename="') + 10
                        filename_end = part.find(b'"', filename_start)
                        filename_bytes = part[filename_start:filename_end]
                        
                        # 尝试多种编码方式解析文件名
                        filename = None
                        for encoding in ['utf-8', 'gbk', 'latin-1']:
                            try:
                                filename = filename_bytes.decode(encoding)
                                break
                            except UnicodeDecodeError:
                                continue
                        
                        if filename is None:
                            filename = filename_bytes.decode('utf-8', errors='replace')
                        
                        # 提取文件内容
                        file_content_start = part.find(b'\r\n\r\n') + 4
                        file_content_end = part.find(b'\r\n--', file_content_start)
                        if file_content_end == -1:
                            file_content_end = len(part) - 2  # 去掉最后的\r\n
                        file_content = part[file_content_start:file_content_end]
                        
                        # 检查文件是否已存在，如果存在则生成新文件名
                        final_filename = self.generate_unique_filename(filename, upload_dir)
                        
                        # 保存文件
                        filepath = os.path.join(upload_dir, final_filename)
                        with open(filepath, 'wb') as f:
                            f.write(file_content)
                        
                        self.send_response(200)
                        self.send_header('Content-Type', 'text/html; charset=utf-8')
                        self.end_headers()
                        
                        if final_filename != filename:
                            response = f'文件已存在，已重命名为: {self.escape_html(final_filename)}<br>'
                        else:
                            response = f'文件上传成功!<br>'
                        
                        response += f'<a href="/browse/{upload_dir}">返回目录</a>'
                        self.wfile.write(response.encode('utf-8'))
                        return
                
                self.send_error(400, "未找到上传的文件")
                
            except Exception as e:
                self.send_error(500, f"上传错误: {str(e)}")
        else:
            self.send_error(404, "未找到页面")
    
    def escape_html(self, text):
        """HTML转义，防止XSS攻击"""
        return (text.replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace('"', '&quot;')
                   .replace("'", '&#39;'))

# 自定义TCPServer，允许地址复用
class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

# 启动服务器
if __name__ == "__main__":
    with ReusableTCPServer(("", PORT), SimpleFileServer) as httpd:
        print(f"文件服务器运行在端口 {PORT}")
        print(f"访问地址: http://localhost:{PORT}")
        print("当前目录:", os.getcwd())
        print("上传重名文件时会自动重命名，格式为: 文件名 (序号).扩展名")
        print("支持子目录浏览，但限制在根目录内")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n服务器已停止")
