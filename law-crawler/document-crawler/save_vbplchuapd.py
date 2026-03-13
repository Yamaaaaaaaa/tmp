import re
from bs4 import BeautifulSoup
import pandas as pd
from sqlalchemy import create_engine
import sqlalchemy.types

# Tạo kết nối với cơ sở dữ liệu
engine = create_engine("mysql+mysqlconnector://root:123456@localhost:3306/law")

print("Đang lấy dữ liệu các văn bản pháp luật từ vbpl...")
# Đọc dữ liệu từ cơ sở dữ liệu
df = pd.read_sql('SELECT id, noidung FROM vbpl;', con=engine)

# Lấy ID lớn nhất hiện tại từ CSDL để tránh trùng khoá chính
try:
    max_id_df = pd.read_sql('SELECT MAX(id) as max_id FROM vbplchuapd;', con=engine)
    id_counter = int(max_id_df.iloc[0]['max_id']) if pd.notna(max_id_df.iloc[0]['max_id']) else 0
except:
    id_counter = 0 

chi_muc = []

for j in range(len(df)):
    contents = df.iloc[j]['noidung']

    if not contents:
        continue
        
    try:
        soup = BeautifulSoup(contents, 'html.parser')
        container = soup.find('div', id='toanvancontent')
        if not container:
            container = soup
        texts = [tag.get_text().replace('\n', ' ').strip() for tag in container.find_all(['p', 'div', 'li', 'h1', 'h2', 'h3', 'h4', 'h5']) if tag.get_text().strip()]
    except Exception as e:
        continue

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
            if i + 1 < len(texts) and texts[i+1].isupper() and not texts[i+1].lower().startswith('chương'):
                ten += ' - ' + texts[i+1].strip()
                i += 1
                
            id_counter += 1
            current_phan = {
                'id': id_counter, 'loai': 'Phần', 'ten': ten, 'noi_dung': '',
                'chi_muc_cha': None
            }
            chi_muc.append(current_phan)
            current_chuong = None; current_muc = None; current_dieu = None
            
        # 2. Phát hiện "Chương"
        elif re.match(r'^Chương\s+[A-Z0-9IVXLC]+', txt, re.IGNORECASE):
            ten = txt
            if i + 1 < len(texts) and texts[i+1].isupper() and not re.match(r'^(mục|điều)', texts[i+1], re.IGNORECASE):
                ten += ' - ' + texts[i+1].strip()
                i += 1
                
            id_counter += 1
            parent_id = current_phan['id'] if current_phan else None
            current_chuong = {
                'id': id_counter, 'loai': 'Chương', 'ten': ten, 'noi_dung': '',
                'chi_muc_cha': parent_id
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
            parent_id = current_chuong['id'] if current_chuong else (current_phan['id'] if current_phan else None)
            current_muc = {
                'id': id_counter, 'loai': 'Mục', 'ten': ten, 'noi_dung': '',
                'chi_muc_cha': parent_id
            }
            chi_muc.append(current_muc)
            current_dieu = None

        # 4. Phát hiện "Điều"
        elif re.match(r'^Điều\s+\d+', txt, re.IGNORECASE):
            ten = txt
            id_counter += 1
            
            parent_id = None
            if current_muc: parent_id = current_muc['id']
            elif current_chuong: parent_id = current_chuong['id']
            elif current_phan: parent_id = current_phan['id']
            
            current_dieu = {
                'id': id_counter, 'loai': 'Điều', 'ten': ten, 'noi_dung': '',
                'chi_muc_cha': parent_id
            }
            chi_muc.append(current_dieu)
            
        # 5. Khác (Nội dung)
        else:
            if current_dieu:
                current_dieu['noi_dung'] += (txt + '\n')
            elif current_muc:
                current_muc['noi_dung'] += (txt + '\n')
            elif current_chuong:
                current_chuong['noi_dung'] += (txt + '\n')
            elif current_phan:
                current_phan['noi_dung'] += (txt + '\n')
        i += 1

# Chuẩn hoá nội dung (xoá khoảng trắng thừa)
for item in chi_muc:
    item['noi_dung'] = item['noi_dung'].strip()

df_to_write = pd.DataFrame(chi_muc)
if not df_to_write.empty:
    df_to_write.to_sql('vbplchuapd', con=engine, if_exists='append', index=False,
                        dtype={
                            'noi_dung': sqlalchemy.types.Text(length=4294967295),
                            'ten': sqlalchemy.types.String(length=1000),      # Cột mở rộng nên có
                            'loai': sqlalchemy.types.String(length=50)        # Cột mở rộng nên có
                        })
    print(f"Đã cập nhật {len(df_to_write)} bản ghi vào bảng vbplchuapd")
