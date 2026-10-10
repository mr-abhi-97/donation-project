import urllib.request
import urllib.parse
import json
import io
import pandas as pd
from PIL import Image, ImageDraw

BASE = 'http://localhost:8000/api'

# 1. Test listing donations
req = urllib.request.Request(f'{BASE}/donations/')
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())
    print('1. List donations status:', resp.status, 'Total items:', len(data))
    assert resp.status == 200

# 2. Test bulk upload screenshot
import time
test_utr = f"4289{int(time.time()) % 100000000:08d}"
img_name = f'utr_{test_utr}_amt_7500.png'
img = Image.new('RGB', (300, 150), color=(255, 255, 255))
d = ImageDraw.Draw(img)
d.text((10, 10), f'UPI Ref no: {test_utr}', fill=(0, 0, 0))
d.text((10, 40), 'Amount: 7500.00', fill=(0, 0, 0))
d.text((10, 70), f'Timestamp: {time.time()}', fill=(0, 0, 0))
img_bytes = io.BytesIO()
img.save(img_bytes, format='PNG')

boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
body = (
    f'--{boundary}\r\n'
    f'Content-Disposition: form-data; name="files"; filename="{img_name}"\r\n'
    f'Content-Type: image/png\r\n\r\n'
).encode() + img_bytes.getvalue() + f'\r\n--{boundary}--\r\n'.encode()

req = urllib.request.Request(f'{BASE}/donations/bulk-upload', data=body, headers={
    'Content-Type': f'multipart/form-data; boundary={boundary}'
})
with urllib.request.urlopen(req) as resp:
    upload_res = json.loads(resp.read().decode())
    print('2. Bulk upload status:', resp.status, 'Uploaded items:', len(upload_res))
    assert len(upload_res) >= 1
    test_d = upload_res[0]
    print('   Uploaded UTR:', test_d['extracted_utr'], '| Initial Status:', test_d['status'])
    assert test_d['extracted_utr'] == test_utr
    assert test_d['status'] in ['PENDING', 'EXTRACTED', 'MATCHED']

# 3. Test bank statement upload with matching UTR
df = pd.DataFrame([{
    'Transaction Date': '2024-10-10',
    'Narration': f'UPI/{test_utr}/CR/PHONEPE/DONOR TEST/DONATION',
    'Credit Amount': 7500.00,
    'Balance': 1500000.00
}])
excel_buf = io.BytesIO()
with pd.ExcelWriter(excel_buf, engine='openpyxl') as writer:
    df.to_excel(writer, index=False)
excel_bytes = excel_buf.getvalue()

stmt_boundary = '----WebKitFormBoundaryX9aY7bZ'
stmt_body = (
    f'--{stmt_boundary}\r\n'
    f'Content-Disposition: form-data; name="file"; filename="test_stmt.xlsx"\r\n'
    f'Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n'
).encode() + excel_bytes + f'\r\n--{stmt_boundary}--\r\n'.encode()

req = urllib.request.Request(f'{BASE}/bank-statement/upload', data=stmt_body, headers={
    'Content-Type': f'multipart/form-data; boundary={stmt_boundary}'
})
with urllib.request.urlopen(req) as resp:
    stmt_res = json.loads(resp.read().decode())
    print('3. Bank statement upload status:', resp.status, 'Total donations returned:', len(stmt_res))
    matched_records = [d for d in stmt_res if d['extracted_utr'] == test_utr]
    assert len(matched_records) > 0
    print('   Matched record status:', matched_records[0]['status'], '| is_verified:', matched_records[0]['is_verified'])
    assert matched_records[0]['status'] in ['MATCHED', 'SUCCESS']
    assert matched_records[0]['is_verified'] == True

# 4. Test delete donation
del_id = test_d['id']
req = urllib.request.Request(f'{BASE}/donations/{del_id}', method='DELETE')
with urllib.request.urlopen(req) as resp:
    del_res = json.loads(resp.read().decode())
    print('4. Delete status:', resp.status, del_res)
    assert resp.status == 200

print('\n*** ALL SINGLE-PAGE RECONCILIATION API WORKFLOWS PASSED 100%! ***')
