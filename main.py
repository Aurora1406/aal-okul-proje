from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import pyodbc
import shutil
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Yüklenen görsellerin kaydedileceği klasör
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

DB_CONN_STR = (
    "Driver={ODBC Driver 17 for SQL Server};"
    "Server=.\\SQLEXPRESS;"
    "Database=OkulWeb;"
    "Trusted_Connection=yes;"
)

class Randevu(BaseModel):
    isim: str
    tarih: str
    konu: str

class AdminLogin(BaseModel):
    kullaniciAdi: str
    sifre: str

@app.post("/api/randevu-kaydet")
def randevu_kaydet(randevu: Randevu):
    try:
        conn = pyodbc.connect(DB_CONN_STR)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Randevular (AdSoyad, Tarih, Konu) VALUES (?, ?, ?)",
            (randevu.isim, randevu.tarih, randevu.konu)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return {"mesaj": "Randevu başarıyla kaydedildi."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Veritabanı hatası: {str(e)}")

@app.post("/api/admin-giris")
def admin_giris(veri: AdminLogin):
    if veri.kullaniciAdi == "yonetici" and veri.sifre == "aal2026":
        return {"basarili": True, "mesaj": "Giriş onaylandı."}
    else:
        raise HTTPException(status_code=401, detail="Hatalı kullanıcı adı veya şifre!")

@app.get("/api/randevulari-getir")
def randevulari_getir():
    try:
        conn = pyodbc.connect(DB_CONN_STR)
        cursor = conn.cursor()
        cursor.execute("SELECT ID, AdSoyad, Tarih, Konu, KayitZamani FROM Randevular ORDER BY KayitZamani DESC")
        rows = cursor.fetchall()
        randevular = [{"id": r[0], "adSoyad": r[1], "tarih": str(r[2]), "konu": r[3], "kayitZamani": str(r[4])} for r in rows]
        cursor.close()
        conn.close()
        return {"randevular": randevular}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- YENİ: DUYURU EKLEME API'Sİ (Görsel Destekli) ---
@app.post("/api/duyuru-ekle")
async def duyuru_ekle(
    baslik: str = Form(...),
    icerik: str = Form(...),
    tarih: str = Form(...),
    gorsel: UploadFile = File(None)
):
    try:
        gorsel_yolu = None
        if gorsel:
            dosya_adi = f"{os.urandom(8).hex()}_{gorsel.filename}"
            dosya_yolu = os.path.join(UPLOAD_DIR, dosya_adi)
            with open(dosya_yolu, "wb") as buffer:
                shutil.copyfileobj(gorsel.file, buffer)
            gorsel_yolu = f"/uploads/{dosya_adi}"

        conn = pyodbc.connect(DB_CONN_STR)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Duyurular (Baslik, Icerik, Tarih, GorselYolu) VALUES (?, ?, ?, ?)",
            (baslik, icerik, tarih, gorsel_yolu)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return {"mesaj": "Duyuru başarıyla yayınlandı."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- YENİ: DUYURULARI LİSTELEME API'Sİ ---
@app.get("/api/duyurulari-getir")
def duyurulari_getir():
    try:
        conn = pyodbc.connect(DB_CONN_STR)
        cursor = conn.cursor()
        cursor.execute("SELECT ID, Baslik, Icerik, Tarih, GorselYolu FROM Duyurular ORDER BY Tarih DESC")
        rows = cursor.fetchall()
        duyurular = [{"id": r[0], "baslik": r[1], "icerik": r[2], "tarih": str(r[3]), "gorselYolu": r[4]} for r in rows]
        cursor.close()
        conn.close()
        return {"duyurular": duyurular}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- YENİ: DUYURU SİLME API'Sİ ---
@app.delete("/api/duyuru-sil/{duyuru_id}")
def duyuru_sil(duyuru_id: int):
    try:
        conn = pyodbc.connect(DB_CONN_STR)
        cursor = conn.cursor()
        
        # Önce silinecek duyurunun görseli var mı kontrol edelim (Dosyayı sunucudan da silmek için)
        cursor.execute("SELECT GorselYolu FROM Duyurular WHERE ID = ?", (duyuru_id,))
        row = cursor.fetchone()
        if row and row[0]:
            dosya_yolu = row[0].lstrip("/") # Baştaki / işaretini kaldır
            if os.path.exists(dosya_yolu):
                os.remove(dosya_yolu)
                
        # Veritabanından duyuruyu sil
        cursor.execute("DELETE FROM Duyurular WHERE ID = ?", (duyuru_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return {"mesaj": "Duyuru başarıyla silindi."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from fastapi.responses import HTMLResponse
import os

# Ana dizine girildiğinde anamenu.html dosyasını göster
@app.get("/", response_class=HTMLResponse)
def ana_sayfa():
    if os.path.exists("anamenu.html"):
        with open("anamenu.html", "r", encoding="utf-8") as f:
            return f.read()
    return "Anamenu dosyası bulunamadı!"