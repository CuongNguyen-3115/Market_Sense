from pathlib import Path

def print_dir_tree(directory, prefix="", current_depth=1, max_depth=2):
    """
    In cấu trúc thư mục dưới dạng hình cây với độ sâu giới hạn.
    
    :param directory: Đường dẫn thư mục cần in (chuỗi hoặc Path object)
    :param prefix: Ký tự tiền tố dùng cho đệ quy (để vẽ nhánh)
    :param current_depth: Độ sâu hiện tại (dùng để kiểm tra điều kiện dừng)
    :param max_depth: Độ sâu tối đa muốn in
    """
    # Dừng nếu vượt quá độ sâu cấu hình
    if current_depth > max_depth:
        return

    path = Path(directory)
    
    # Các thư mục/file muốn bỏ qua để cây thư mục gọn gàng
    ignored_items = {'.git', '__pycache__', '.venv', 'venv', '.idea', '.vscode', '.DS_Store'}

    try:
        # Lấy danh sách và sắp xếp: thư mục lên trước, file theo sau
        items = sorted(
            [node for node in path.iterdir() if node.name not in ignored_items],
            key=lambda x: (x.is_file(), x.name.lower())
        )
    except PermissionError:
        # Bỏ qua nếu gặp thư mục không có quyền truy cập
        return

    for i, item in enumerate(items):
        # Kiểm tra xem đây có phải là item cuối cùng trong thư mục hiện tại không
        is_last = (i == len(items) - 1)
        connector = "└── " if is_last else "├── "
        
        # In tên file/thư mục kèm ký tự nhánh
        print(f"{prefix}{connector}{item.name}/" if item.is_dir() else f"{prefix}{connector}{item.name}")
        
        # Nếu là thư mục, tiếp tục đệ quy xuống tầng sâu hơn
        if item.is_dir():
            next_prefix = prefix + ("    " if is_last else "│   ")
            print_dir_tree(item, next_prefix, current_depth + 1, max_depth)

if __name__ == "__main__":
    # "." đại diện cho thư mục dự án hiện tại chứa file script này
    project_root = "." 
    
    # THAY ĐỔI ĐỘ SÂU BẠN MUỐN Ở ĐÂY (ví dụ: max_depth=1, max_depth=2, max_depth=3)
    target_depth = 2 
    
    print(f" Gốc dự án: {Path(project_root).resolve().name}")
    print_dir_tree(project_root, max_depth=target_depth)