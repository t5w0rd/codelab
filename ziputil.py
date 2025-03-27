import struct
import os
import proto

class ZipFile:
    data: bytearray
    off_eocd: int
    filename: str
    
    def __init__(self, name: str):
        self.filename = name
        self.data = self.load_file(name)
        
        if not self.check_header():
            raise Exception('Invalid zip file, PK0304 not found')
        
        off_eocd = self.find_eocd()
        if off_eocd < 0:
            raise Exception('Invalid zip file, PK0506 not found')
        self.off_eocd = off_eocd
        

    def load_file(self, name: str) -> bytearray:
        with open(name, 'rb') as f:
            data = bytearray(f.read())
            self.data = data
            return data


    def save_file(self, name: str, data: bytearray) -> None:
        with open(name, 'wb') as f:
            f.write(data)


    def check_header(self) -> bool:
        if self.data[:4] != b'PK\x03\x04':
            return False
        return True


    def find_eocd(self) -> int:
        eocd_list = []
        for i in range(len(self.data)):
            if self.data[i:i+4] == b'PK\x05\x06':
                eocd_list.append(i)
        if len(eocd_list) == 0:
            return -1
        if len(eocd_list) > 1:
            raise Exception('Invalid zip file, multiple EOCD records found')
        return eocd_list[-1]
        
    
    def fix_zip(self) -> None:
        # 读取注释长度，位于EOCD记录的第20-21字节
        comment_len = struct.unpack('<H', self.data[self.off_eocd+20:self.off_eocd+22])[0]
        
        # 计算预期的文件结束位置
        expected_end = self.off_eocd + 22 + comment_len
        actual_size = len(self.data)
        
        # 检查是否有足够的数据
        if expected_end > actual_size:
            print(f"ZIP文件异常：注释长度为{comment_len}，但实际数据不足")
            
            # 修复ZIP文件：将注释长度设置为0
            self.data[self.off_eocd+20:self.off_eocd+22] = struct.pack('<H', 0)
            
            # 分离有效的ZIP数据和额外数据
            valid_zip_data = self.data[:self.off_eocd+22]  # EOCD记录结束位置
            extra_data = self.data[self.off_eocd+22:]
            
            # 生成新文件名
            base_name, ext = os.path.splitext(self.filename)
            fixed_zip_name = f"{base_name}_fix{ext}"
            extra_data_name = f"{base_name}_ext.bin"
            
            # 保存修复后的ZIP文件和额外数据
            self.save_file(fixed_zip_name, valid_zip_data)
            if extra_data:
                self.save_file(extra_data_name, extra_data)
            
            print(f"已修复ZIP文件并保存为：{fixed_zip_name}")
            if extra_data:
                print(f"额外数据已保存为：{extra_data_name}")
        elif expected_end < actual_size:
            print(f"ZIP文件末尾存在多余数据：预期结束位置为{expected_end}，实际大小为{actual_size}")
            
            # 分离有效的ZIP数据和多余数据
            valid_zip_data = self.data[:expected_end]  # 包含完整的ZIP文件（含注释）
            extra_data = self.data[expected_end:]
            
            # 生成新文件名
            base_name, ext = os.path.splitext(self.filename)
            fixed_zip_name = f"{base_name}_fix{ext}"
            extra_data_name = f"{base_name}_ext.bin"
            
            # 保存正常的ZIP文件和多余数据
            self.save_file(fixed_zip_name, valid_zip_data)
            self.save_file(extra_data_name, extra_data)
            
            print(f"已分离ZIP文件和多余数据")
            print(f"正常ZIP文件已保存为：{fixed_zip_name}")
            print(f"多余数据已保存为：{extra_data_name}")
        else:
            print("ZIP文件正常，无需修复")


def load_file(name: str) -> bytearray:
        with open(name, 'rb') as f:
            return bytearray(f.read())


def save_file(name: str, data: bytearray) -> None:
    with open(name, 'wb') as f:
        f.write(data)


def scan_files(data):
    for i in range(len(data)):
        if data[i:i+4] == b'PK\x03\x04':
            name_len = struct.unpack('<H', data[i+26:i+26+2])[0]
            print(f'file_name({name_len}): [{data[i+30:i+30+name_len].decode('utf8')}]')
        elif data[i:i+4] == b'PK\x05\x06':
            print(f'eocd: -{len(data)-i}')


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python ziputil.py <zip文件路径>")
        sys.exit(1)
    
    try:
        data = load_file(sys.argv[1])
        scan_files(data)
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)
