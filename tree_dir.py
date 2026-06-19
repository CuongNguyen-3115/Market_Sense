from pathlib import Path

def print_tree(dir_path: Path, max_depth: int = 2, current_depth: int = 0, exclude_dirs: list = None):
    """
    Hàm in ra cây cấu trúc thư mục từ một vị trí chỉ định.
    - dir_path: Thư mục gốc bắt đầu in.
    - max_depth: Độ sâu tối đa.
    - current_depth: Biến đếm độ sâu đệ quy.
    - exclude_dirs: Danh sách các thư mục muốn ẩn đi.
    """
    if exclude_dirs is None:
        exclude_dirs = []
        
    # Kiểm tra xem đường dẫn được chỉ định có tồn tại không (chỉ check ở lượt gọi đầu tiên)
    if current_depth == 0 and not dir_path.exists():
        print(f"❌ Đường dẫn không tồn tại: {dir_path}")
        return

    exclude_resolved = [p.resolve() for p in exclude_dirs]
    
    if current_depth > max_depth:
        return
        
    indent = "    " * (current_depth - 1) if current_depth > 0 else ""
    
    if current_depth == 0:
        # In tên thư mục chỉ định làm gốc
        print(f"📁 {dir_path.resolve().name}/  ({dir_path.resolve()})")
    else:
        branch = "├── "
        icon = "📁" if dir_path.is_dir() else "📄"
        print(f"{indent}{branch}{icon} {dir_path.name}")
        
    if dir_path.is_dir() and current_depth < max_depth:
        try:
            children = sorted(dir_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
            for child in children:
                if child.resolve() in exclude_resolved:
                    continue 
                    
                print_tree(child, max_depth, current_depth + 1, exclude_dirs)
        except PermissionError:
            error_indent = "    " * current_depth
            print(f"{error_indent}├── 🚫 [Không có quyền truy cập]")

if __name__ == "__main__":
    # Đặt chính xác thư mục bạn muốn in cấu trúc (Sử dụng raw string r"...")
    target_dir = Path(r"C:\1. Project\2_Cuộc_thi\2026\3. HACK CX TOGETHER 2026\market_sense\frontend")
    
    # Bạn vẫn có thể giữ hoặc thêm các thư mục muốn loại trừ ở đây nếu cần
    folders_to_ignore = [
        # Path(r"C:\1. Project\ĐATN\logs") 
    ]
    
    # Tiến hành in cấu trúc thư mục mục tiêu với độ sâu cấp 2
    print_tree(target_dir, max_depth=3, exclude_dirs=folders_to_ignore)