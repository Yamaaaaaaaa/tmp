import re
from bs4 import BeautifulSoup
import pandas as pd
from sqlalchemy import create_engine
import sqlalchemy.types
# Tạo kết nối với cơ sở dữ liệu
engine = create_engine("mysql+mysqlconnector://root:123456789@localhost:3306/law")
# Đọc dữ liệu từ cơ sở dữ liệu
df = pd.read_sql('SELECT id, noidung FROM vbpl;', con=engine)
# Cải tiến: Tự động lấy ID lớn nhất hiện tại từ CSDL để tránh trùng khoá chính
try:
    max_id_df = pd.read_sql('SELECT MAX(id) as max_id FROM vbplchimuc;', con=engine)
    id_counter = int(max_id_df.iloc[0]['max_id']) if pd.notna(max_id_df.iloc[0]['max_id']) else 0
except:
    id_counter = 3012 # Giá trị mặc định nếu table trống
chi_muc = []
for j in range(len(df)):
    id_vb = df.iloc[j]['id']
    contents = df.iloc[j]['noidung']
    
    if not contents:
        continue
        
    try:
        # Nhắm vào thẻ div có id 'toanvancontent', fallback về toàn bộ BeautifulSoup nếu không có
        soup = BeautifulSoup(contents, 'html.parser')
        container = soup.find('div', id='toanvancontent')
        if not container:
            container = soup
            
        # Lấy văn bản từ các thẻ block thông dụng thay vì chỉ mỗi thẻ p
        texts = [tag.get_text().replace('\n', ' ').strip() for tag in container.find_all(['p', 'div', 'li', 'h1', 'h2', 'h3', 'h4', 'h5']) if tag.get_text().strip()]
    except Exception as e:
        continue
    # Khởi tạo các pointer giữ dấu vết của phân cấp cao hơn
    current_phan = None
    current_chuong = None
    current_muc = None
    current_dieu = None
    i = 0
    while i < len(texts):
        txt = texts[i]
        
        # 1. Phát hiện "Phần"
        if re.match(r'^Phần\s+[A-Z0-9IVXLC]+', txt, re.IGNORECASE):
            ten = txt
            # Quét xem dòng kế tiếp có phải là tên chi tiết in hoa (ví dụ: QUY ĐỊNH CHUNG) không
            if i + 1 < len(texts) and texts[i+1].isupper() and not texts[i+1].lower().startswith('chương'):
                ten += ' - ' + texts[i+1].strip()
                i += 1
                
            id_counter += 1
            current_phan = {
                'id': id_counter, 'loai': 'Phần', 'ten': ten, 'noi_dung': '',
                'chi_muc_cha': None, 'id_vb': id_vb
            }
            chi_muc.append(current_phan)
            # Reset các pointer phân cấp dưới
            current_chuong = None; current_muc = None; current_dieu = None
            
        # 2. Phát hiện "Chương"
        elif re.match(r'^Chương\s+[A-Z0-9IVXLC]+', txt, re.IGNORECASE):
            ten = txt
            if i + 1 < len(texts) and texts[i+1].isupper() and not re.match(r'^(mục|điều)', texts[i+1], re.IGNORECASE):
                ten += ' - ' + texts[i+1].strip()
                i += 1
                
            id_counter += 1
            # Cha của Chương có thể là Phần hoặc None
            parent_id = current_phan['id'] if current_phan else None
            current_chuong = {
                'id': id_counter, 'loai': 'Chương', 'ten': ten, 'noi_dung': '',
                'chi_muc_cha': parent_id, 'id_vb': id_vb
            }
            chi_muc.append(current_chuong)
            current_muc = None; current_dieu = None
        # 3. Phát hiện "Mục"
        elif re.match(r'^Mục\s+\d+', txt, re.IGNORECASE):
            ten = txt
            if i + 1 < len(texts) and (texts[i+1].isupper() or len(texts[i+1].split()) <= 15) and not re.match(r'^điều', texts[i+1], re.IGNORECASE):
                ten += ' - ' + texts[i+1].strip()
                i += 1
                
            id_counter += 1
            # Cha của Mục là Chương hoặc Phần 
            parent_id = current_chuong['id'] if current_chuong else (current_phan['id'] if current_phan else None)
            current_muc = {
                'id': id_counter, 'loai': 'Mục', 'ten': ten, 'noi_dung': '',
                'chi_muc_cha': parent_id, 'id_vb': id_vb
            }
            chi_muc.append(current_muc)
            current_dieu = None
        # 4. Phát hiện "Điều"
        elif re.match(r'^Điều\s+\d+', txt, re.IGNORECASE):
            # Với Điều thì thường Tên Điều nằm chung 1 dòng luôn (vd: "Điều 1. Phạm vi điều chỉnh")
            ten = txt
            id_counter += 1
            
            # Cha của "Điều" chiếu từ cấp thấp dần lên xem có thằng nào ko
            parent_id = None
            if current_muc: parent_id = current_muc['id']
            elif current_chuong: parent_id = current_chuong['id']
            elif current_phan: parent_id = current_phan['id']
            
            current_dieu = {
                'id': id_counter, 'loai': 'Điều', 'ten': ten, 'noi_dung': '',
                'chi_muc_cha': parent_id, 'id_vb': id_vb
            }
            chi_muc.append(current_dieu)
            
        # 5. Các dòng còn lại: Được coi là nội dung của văn bản
        else:
            # Ưu tiên cộng gộp vào cấp nhỏ nhất mà nó đang trực thuộc (chủ yếu là "Điều")
            if current_dieu:
                current_dieu['noi_dung'] += (txt + '\n')
            elif current_muc:
                current_muc['noi_dung'] += (txt + '\n')
            elif current_chuong:
                current_chuong['noi_dung'] += (txt + '\n')
            elif current_phan:
                current_phan['noi_dung'] += (txt + '\n')
        i += 1
# Normalize xoá đi các dấu xuống dòng ở đầu và cuối nội dung thừa thãi
for item in chi_muc:
    item['noi_dung'] = item['noi_dung'].strip()
df_to_write = pd.DataFrame(chi_muc)
if not df_to_write.empty:
    df_to_write.to_sql('vbplchimuc', con=engine, if_exists='append', index=False,
                        dtype={
                            'noi_dung': sqlalchemy.types.Text(length=4294967295),
                            'ten': sqlalchemy.types.String(length=1000),
                            'loai': sqlalchemy.types.String(length=50)
                        })
    print(f"Đã cập nhật {len(df_to_write)} bản ghi vào bảng vbplchimuc")