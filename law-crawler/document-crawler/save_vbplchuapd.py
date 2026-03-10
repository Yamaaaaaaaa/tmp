import pandas as pd
from sqlalchemy import create_engine
import sqlalchemy.types
import re

# Tạo kết nối với cơ sở dữ liệu
engine = create_engine("mysql+mysqlconnector://root:123456789@localhost:3306/law")

print("Đang đọc dữ liệu từ vbpldaydu để lấy danh sách id hợp lệ...")
df_vbpldaydu = pd.read_sql('SELECT id FROM vbpldaydu;', con=engine)
valid_id_vbs = set(df_vbpldaydu['id'])

print("Đang đọc dữ liệu từ pddieu...")
# Đọc dữ liệu từ pddieu để lấy ánh xạ id_vb -> demuc_id
df_pddieu = pd.read_sql('SELECT vbqppl_link, demuc_id FROM pddieu WHERE vbqppl_link IS NOT NULL GROUP BY vbqppl_link, demuc_id;', con=engine)

def get_item_id(url):
    if not url:
        return None
    match = re.search(r'ItemID=(\d+)', url)
    if match:
        return int(match.group(1))
    return None

df_pddieu['id_vb'] = df_pddieu['vbqppl_link'].apply(get_item_id)
# Loại bỏ các dòng không parser được id_vb
df_pddieu = df_pddieu.dropna(subset=['id_vb'])

# Lấy mapping id_vb -> demuc_id (nếu 1 id_vb có nhiều demuc_id, tạm lấy cái đầu tiên)
mapping_demuc = dict(zip(df_pddieu['id_vb'], df_pddieu['demuc_id']))

print("Đang đọc dữ liệu từ vb_chimuc...")
# Đọc dữ liệu các chỉ mục từ vb_chimuc
df_chimuc = pd.read_sql('SELECT id, id_vb, noi_dung FROM vb_chimuc;', con=engine)

print(f"Tổng số row trong vb_chimuc: {len(df_chimuc)}")

# Chuẩn bị dữ liệu insert vào vbplchuapd
data_to_insert = []
for index, row in df_chimuc.iterrows():
    id_vb = row['id_vb']
    demuc_id = mapping_demuc.get(id_vb)
    
    # Chỉ lưu nếu tìm thấy demuc_id tương ứng và id_vb tồn tại trong bảng vbpldaydu
    if demuc_id and id_vb in valid_id_vbs:
        data_to_insert.append({
            'noi_dung': row['noi_dung'],
            'chi_muc_cha': row['id'],      # Tham chiếu tới id của vb_chimuc (ChiMucVBPL)
            'id_vb': id_vb,                  # Tham chiếu tới vbpldaydu
            'demuc_id': demuc_id             # Tham chiếu tới pddemuc
        })

df_to_write = pd.DataFrame(data_to_insert)

if not df_to_write.empty:
    print(f"Đang ghi {len(df_to_write)} bản ghi vào bảng vbplchuapd...")
    df_to_write.to_sql('vbplchuapd', con=engine, if_exists='append', index=False,
                        dtype={'noi_dung': sqlalchemy.types.Text(length=4294967295)})
    print("Mọi dữ liệu đã được lưu thành công!")
else:
    print("Không có dữ liệu nào cần lưu.")
