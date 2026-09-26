from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import shutil
import sqlite3
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

# SQLite Veritabanı Dosyası
DB_FILE = "okul.db"

# Veritabanı ve tabloları otomatik oluşturan fonksiyon
def veritabani_baslat():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Randevular tablosu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Randevular (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            AdSoyad TEXT,
            Tarih TEXT,
            Konu TEXT,
            KayitZamani TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Duyurular tablosu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Duyurular (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            Baslik TEXT,
            Icerik TEXT,
            Tarih TEXT,
            GorselYolu TEXT
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

# Uygulama ayağa kalkarken tabloları otomatik oluştur
veritabani_baslat()

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
        conn = sqlite3.connect(DB_FILE)
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
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT ID, AdSoyad, Tarih, Konu, KayitZamani FROM Randevular ORDER BY KayitZamani DESC")
        rows = cursor.fetchall()
        randevular = [{"id": r[0], "adSoyad": r[1], "tarih": str(r[2]), "konu": r[3], "kayitZamani": str(r[4])} for r in rows]
        cursor.close()
        conn.close()
        return {"randevular": randevular}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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

        conn = sqlite3.connect(DB_FILE)
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

@app.get("/api/duyurulari-getir")
def duyurulari_getir():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT ID, Baslik, Icerik, Tarih, GorselYolu FROM Duyurular ORDER BY Tarih DESC")
        rows = cursor.fetchall()
        duyurular = [{"id": r[0], "baslik": r[1], "icerik": r[2], "tarih": str(r[3]), "gorselYolu": r[4]} for r in rows]
        cursor.close()
        conn.close()
        return {"duyurular": duyurular}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/duyuru-sil/{duyuru_id}")
def duyuru_sil(duyuru_id: int):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT GorselYolu FROM Duyurular WHERE ID = ?", (duyuru_id,))
        row = cursor.fetchone()
        if row and row[0]:
            dosya_yolu = row[0].lstrip("/")
            if os.path.exists(dosya_yolu):
                os.remove(dosya_yolu)
                
        cursor.execute("DELETE FROM Duyurular WHERE ID = ?", (duyuru_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return {"mesaj": "Duyuru başarıyla silindi."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", response_class=HTMLResponse)
def ana_sayfa():
    if os.path.exists("anamenu.html"):
        with open("anamenu.html", "r", encoding="utf-8") as f:
            return f.read()
    return "Anamenu dosyası bulunamadı!"

@app.get("/admin.html", response_class=HTMLResponse)
def admin_sayfa():
    if os.path.exists("admin.html"):
        with open("admin.html", "r", encoding="utf-8") as f:
            return f.read()
    return "Admin dosyası bulunamadı!"