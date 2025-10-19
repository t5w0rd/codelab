#!/usr/bin/env python
import plistlib
import os
from PIL import Image
import re
import argparse

def parse_rect(rect_str):
    """
    解析矩形字符串格式，支持两种格式：
    1. {{x, y}, {width, height}}
    2. {width, height}
    
    参数:
    rect_str (str): 矩形字符串
    
    返回:
    tuple: (x, y, width, height)
    """
    # 尝试解析第一种格式：{{x, y}, {width, height}}
    match = re.match(r'\{\{(\d+),\s*(\d+)\},\s*\{(\d+),\s*(\d+)\}\}', rect_str)
    if match:
        return tuple(map(int, match.groups()))
    
    # 尝试解析第二种格式：{width, height}
    match = re.match(r'\{\s*(\d+),\s*(\d+)\s*\}', rect_str)
    if match:
        # 对于尺寸字符串，返回 (0, 0, width, height)
        return (0, 0, int(match.group(1)), int(match.group(2)))
    
    raise ValueError(f"Invalid rect format: {rect_str}")

def extract_all_frames(plist_path):
    """
    从plist文件中提取所有帧数据并解压图片
    
    参数:
    plist_path (str): plist文件路径
    """
    # 验证文件路径
    if not os.path.exists(plist_path):
        raise FileNotFoundError(f"Plist file not found: {plist_path}")
    
    # 获取基础路径和名称
    base_dir = os.path.dirname(plist_path)
    base_name = os.path.splitext(os.path.basename(plist_path))[0]
    atlas_path = os.path.join(base_dir, f"{base_name}.png")
    output_dir = os.path.join(base_dir, base_name)
    
    # 验证图集文件是否存在
    if not os.path.exists(atlas_path):
        raise FileNotFoundError(f"Atlas image not found: {atlas_path}")
    
    # 加载plist文件
    with open(plist_path, 'rb') as f:
        plist_data = plistlib.load(f)
    
    # 获取帧数据
    frames_data = plist_data.get('frames', {})
    if not frames_data:
        raise ValueError("No frame data found in plist file")
    
    # 加载图集图片
    atlas_img = Image.open(atlas_path)
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 处理所有帧
    processed_frames = set()
    for frame_name, frame_data in frames_data.items():
        # 跳过已经处理过的帧（通过别名处理）
        if frame_name in processed_frames:
            continue
            
        # 提取主帧
        frame_img = extract_single_frame(atlas_img, frame_data)
        processed_frames.add(frame_name)
        
        # 保存主帧
        output_path = os.path.join(output_dir, frame_name)
        frame_img.save(output_path)
        print(f"Extracted frame: {frame_name}")
        
        # 处理别名帧
        aliases = frame_data.get('aliases', [])
        for alias_name in aliases:
            # 保存别名帧（使用相同的图片）
            alias_path = os.path.join(output_dir, alias_name)
            frame_img.save(alias_path)
            processed_frames.add(alias_name)
            print(f"Extracted alias: {alias_name} -> {frame_name}")

def extract_single_frame(atlas_img, frame_data):
    """
    从图集中提取单个帧的图片，并恢复到原始尺寸
    
    参数:
    atlas_img (PIL.Image): 图集图片对象
    frame_data (dict): 帧数据字典
    
    返回:
    PIL.Image: 提取并恢复到原始尺寸的帧图片
    """
    # 解析纹理矩形区域
    texture_rect = parse_rect(frame_data["textureRect"])
    x, y, w, h = texture_rect
    
    # 裁剪图集中的对应区域
    frame_img = atlas_img.crop((x, y, x + w, y + h))
    
    # 处理旋转
    if frame_data["textureRotated"]:
        frame_img = frame_img.transpose(Image.ROTATE_90)
        # 旋转后宽高交换
        w, h = h, w
    
    # 解析精灵颜色矩形（有效区域）
    color_rect = parse_rect(frame_data["spriteColorRect"])
    cx, cy, cw, ch = color_rect
    
    # 解析原始尺寸
    source_size = parse_rect(frame_data["spriteSourceSize"])
    _, _, sw, sh = source_size
    
    # 检查裁剪后的尺寸是否匹配
    if (w, h) != (cw, ch):
        # 如果不匹配，进行二次裁剪（确保尺寸正确）
        frame_img = frame_img.crop((0, 0, cw, ch))
    
    # 创建原始尺寸的透明背景
    original_img = Image.new('RGBA', (sw, sh), (0, 0, 0, 0))
    
    # 将有效区域放置到原始尺寸的正确位置
    original_img.paste(frame_img, (cx, cy))
    
    return original_img

def main():
    # 设置命令行参数
    parser = argparse.ArgumentParser(description='Extract frames from TexturePacker atlas')
    parser.add_argument('plist', help='Path to the .plist file')
    args = parser.parse_args()
    
    # 执行解压
    try:
        extract_all_frames(args.plist)
        print("Extraction completed successfully!")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()