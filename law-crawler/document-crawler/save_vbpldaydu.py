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
        # Lấy văn bản từ các thẻ block thông dụng
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
                
            current_phan = {
                'loai': 'Phần', 'ten': ten, 'noidung': ''
            }
            chi_muc.append(current_phan)
            current_chuong = None; current_muc = None; current_dieu = None
            
        # 2. Phát hiện "Chương"
        elif re.match(r'^Chương\s+[A-Z0-9IVXLC]+', txt, re.IGNORECASE):
            ten = txt
            if i + 1 < len(texts) and texts[i+1].isupper() and not re.match(r'^(mục|điều)', texts[i+1], re.IGNORECASE):
                ten += ' - ' + texts[i+1].strip()
                i += 1
                
            current_chuong = {
                'loai': 'Chương', 'ten': ten, 'noidung': ''
            }
            chi_muc.append(current_chuong)
            current_muc = None; current_dieu = None

        # 3. Phát hiện "Mục"
        elif re.match(r'^Mục\s+\d+', txt, re.IGNORECASE):
            ten = txt
            if i + 1 < len(texts) and (texts[i+1].isupper() or len(texts[i+1].split()) <= 15) and not re.match(r'^điều', texts[i+1], re.IGNORECASE):
                ten += ' - ' + texts[i+1].strip()
                i += 1
                
            current_muc = {
                'loai': 'Mục', 'ten': ten, 'noidung': ''
            }
            chi_muc.append(current_muc)
            current_dieu = None

        # 4. Phát hiện "Điều"
        elif re.match(r'^Điều\s+\d+', txt, re.IGNORECASE):
            ten = txt
            current_dieu = {
                'loai': 'Điều', 'ten': ten, 'noidung': ''
            }
            chi_muc.append(current_dieu)
            
        # 5. Khác (Nội dung)
        else:
            if current_dieu:
                current_dieu['noidung'] += (txt + '\n')
            elif current_muc:
                current_muc['noidung'] += (txt + '\n')
            elif current_chuong:
                current_chuong['noidung'] += (txt + '\n')
            elif current_phan:
                current_phan['noidung'] += (txt + '\n')
        i += 1

# Chuẩn hoá nội dung (xoá khoảng trắng thừa)
for item in chi_muc:
    item['noidung'] = item['noidung'].strip()

# BẢNG MỚI: vbplaydaydu chỉ yêu cầu id(auto_increment), loai, noidung, ten.
# Không lưu ID cha hay ID văn bản, nên ta có thể lọc bỏ các dict rỗng nội dung nếu muốn (tuỳ nghiệp vụ, ở đây tôi giữ nguyên cấu trúc)
df_to_write = pd.DataFrame(chi_muc)
if not df_to_write.empty:
    df_to_write.to_sql('vbpldaydu', con=engine, if_exists='append', index=False,
                        dtype={
                            'loai': sqlalchemy.types.String(length=255),
                            'noidung': sqlalchemy.types.Text(length=4294967295),
                            'ten': sqlalchemy.types.String(length=1000)
                        })
    print(f"Đã cập nhật {len(df_to_write)} bản ghi vào bảng vbpldaydu")
