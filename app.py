from flask import Flask, render_template, request, redirect, url_for, session, make_response,flash, jsonify
from flask_sqlalchemy import SQLAlchemy 
from sqlalchemy import Enum as SQLEnum
from enum import Enum
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__, template_folder='pages')

app.secret_key = 'your_secret_key'

# Konfigurasi koneksi database (ubah sesuai kebutuhan)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/absensidanmonitoring'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inisialisasi database
db = SQLAlchemy(app)

# definisi tabel Pegawai 
class Pegawai(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama_pegawai = db.Column(db.String(100), nullable=False)  
    divisi_id = db.Column(db.Integer, db.ForeignKey('divisi.id'), nullable=True)  # Relasi ke tabel Divisi
    username = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='pegawai')

    divisi = db.relationship('Divisi', backref=db.backref('pegawai', lazy=True))  # Relasi ke objek Divisi

    def __repr__(self):
        return f"<Pegawai {self.nama_pegawai} ({self.username})>"

    
# tabel divisi untuk pegawai
class Divisi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama_divisi = db.Column(db.String(50), nullable=False, unique=True)

    def __repr__(self):
        return f"<Divisi {self.nama_divisi}>"

# definisi tabel konfigurasi kamera presensi
class RoleKamera(Enum):
    IN = "in"
    OUT = "out"

class KonfigurasiKamerapresensi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama_kamera = db.Column(db.String(100), nullable=False, unique=True)
    role_kamera = db.Column(SQLEnum(RoleKamera), nullable=False)  # Hanya bisa "in" atau "out"
    ip_rtsp = db.Column(db.String(255), nullable=False, unique=True)
    jam_mulai_kedatangan = db.Column(db.Time, nullable=False)
    jam_berakhir_kedatangan = db.Column(db.Time, nullable=False)
    jam_mulai_pulang = db.Column(db.Time, nullable=False)
    jam_berakhir_pulang = db.Column(db.Time, nullable=False)

    def __repr__(self):
        return f"<KonfigurasiKamerapresensi {self.nama_kamera} ({self.role_kamera.value})>"

# definisi tabel konfigurasi kamera pelacakan kerja
class KonfigurasiKamerapelacakankerja(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama_kamera = db.Column(db.String(100), nullable=False, unique=True)
    ip_rtsp = db.Column(db.String(255), nullable=False, unique=True)
   
    def __repr__(self):
        return f"<KonfigurasiKamerapelacakankerja {self.nama_kamera})>"

# definisi tabel Superadmin 
class Superadmin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='superadmin')  

    def __repr__(self):
        return f"<Superadmin {self.username}>"
    
# definisi tabel admin 
class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    id_perusahaan = db.Column(db.Integer, nullable=False)  # ID Perusahaan
    nama_perusahaan = db.Column(db.String(100), nullable=False)  # Nama Perusahaan
    username = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='admin') 

    def __repr__(self):
        return f"<Admin {self.username} - {self.nama_perusahaan}>"


@app.route('/')
def index():
    return redirect(url_for('login'))  


# route untuk login
@app.route('/sign-in', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Ambil user berdasarkan username (baik Superadmin atau Pegawai)
        user = Admin.query.filter_by(username=username).first() or Pegawai.query.filter_by(username=username).first() or Superadmin.query.filter_by(username=username).first()


        if user:
            # Cek apakah password yang diinput sesuai dengan hash password yang ada di database
            if user.password == password:  # Bandingkan password yang diinput dengan hash
                # Simpan sesi login
                session['user_id'] = user.id
                session['username'] = user.username
                session['role'] = user.role  # Simpan role

                # Set cookies sebelum redirect
                response = make_response(redirect(url_for('super_admin_dashboard' if user.role == 'superadmin' 
                                                        else 'admin_dashboard' if user.role == 'admin' 
                                                        else 'pegawai_dashboard ')))
                response.set_cookie('user_id', str(user.id), max_age=3600)  # Simpan cookies
                response.set_cookie('username', user.username, max_age=3600)
                response.set_cookie('role', user.role, max_age=3600)


                
                # Arahkan berdasarkan role
                if user.role == 'superadmin':
                    return redirect(url_for('super_admin_dashboard'))
                elif user.role == 'admin':
                    return redirect(url_for('admin_dashboard'))
                elif user.role == 'pegawai':
                    return redirect(url_for('pegawai_dashboard'))
            else:
                return "Password salah!"  # Pesan jika password tidak cocok
        else:
            return "Username tidak ditemukan!"  # Pesan jika username tidak ditemukan

    return render_template('sign-in.html')

# Route Dashboard Superadmin
@app.route('/super_admin_dashboard', methods=['GET', 'POST'])
def super_admin_dashboard():
    if 'user_id' not in session or session['role'] != 'superadmin':
        return redirect(url_for('login'))  # Jika belum login atau bukan superadmin, redirect ke login

    # Ambil daftar admin
    admins = Pegawai.query.filter_by(role='admin').all()

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Enkripsi password sebelum disimpan
        hashed_password = generate_password_hash(password)

        # Simpan akun admin baru ke database
        new_admin = Pegawai(username=username, password=hashed_password, role='admin')
        db.session.add(new_admin)
        db.session.commit()

        return redirect(url_for('super_admin_dashboard'))  # Redirect kembali ke halaman dashboard

    return render_template('super_admin_dashboard.html', username=session['username'], admins=admins)

# Route untuk menampilkan halaman admin
@app.route('/super-admin/user', methods=['GET', 'POST'])
def super_admin_user():
    if request.method == 'POST':
        id_perusahaan = request.form.get('id_perusahaan')
        nama_perusahaan = request.form.get('nama_perusahaan')
        username = request.form.get('username')
        password = request.form.get('password')

        if not (id_perusahaan and nama_perusahaan and username and password):
            flash('Semua field harus diisi!', 'danger')
            return redirect(url_for('super_admin_user'))

        # Debugging log
        print(f"Data diterima: {id_perusahaan}, {nama_perusahaan}, {username}")

        # Cek apakah username sudah ada
        existing_user = Admin.query.filter_by(username=username).first()
        if existing_user:
            flash('Username sudah digunakan!', 'danger')
            return redirect(url_for('super_admin_user'))

        try:
            
            new_admin = Admin(
                id_perusahaan=id_perusahaan,
                nama_perusahaan=nama_perusahaan,
                username=username,
                password=password
            )
            db.session.add(new_admin)
            db.session.commit()
            flash('Admin berhasil ditambahkan!', 'success')
        except Exception as e:
            db.session.rollback()
            print(f"Error: {str(e)}")  # Debugging log
            flash(f'Error: {str(e)}', 'danger')

        return redirect(url_for('super_admin_user'))

    admins = Admin.query.all()
    # Passing the admins to the template
    return render_template('super_admin_user.html', admins=admins)



# Route Dashboard Admin
@app.route('/divisi_dashboard')
def admin_dashboard():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))  # Jika belum login atau bukan admin, redirect ke login
    return render_template('divisi_dashboard.html', username=session['username'])


# Route untuk halaman divisi_divisi
@app.route('/divisi_divisi')
def divisi_divisi():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))  
    pegawai_list = Pegawai.query.all()  
    divisi_list = Divisi.query.all() 
    pegawai_list = Pegawai.query.all()  # Fetch all employees
    return render_template('divisi_divisi.html', username=session['username'], pegawai_list=pegawai_list, divisi_list=divisi_list)

#route tambah divisi
@app.route('/add_divisi', methods=['POST'])
def add_divisi():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))  # Redirect jika tidak login atau bukan admin

    nama_divisi = request.form.get('nama_divisi', '').strip()

    if not nama_divisi:
        flash('Nama divisi tidak boleh kosong!', 'danger')
        return redirect(url_for('divisi_divisi'))

    # Cek apakah divisi sudah ada
    existing_divisi = Divisi.query.filter_by(nama_divisi=nama_divisi).first()
    if existing_divisi:
        flash(f'Divisi "{nama_divisi}" sudah ada!', 'warning')
    else:
        # Tambahkan divisi ke database
        new_divisi = Divisi(nama_divisi=nama_divisi)
        db.session.add(new_divisi)
        db.session.commit()
        flash(f'Divisi "{nama_divisi}" berhasil ditambahkan!', 'success')

    return redirect(url_for('divisi_divisi'))

# Route Divisi_pegawai
@app.route('/divisi_pegawai')
def divisi_pegawai():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    
    divisi_list = Divisi.query.all()  # Mengambil semua data divisi dari database
    pegawai_list = Pegawai.query.all()
    return render_template('divisi_pegawai.html', divisi_list=divisi_list,pegawai_list=pegawai_list)

# route tambah_pegawai
@app.route('/tambah_pegawai', methods=['GET', 'POST'])
def tambah_pegawai():
    if request.method == 'POST':
        # Ambil data dari form
        nama_pegawai = request.form['nama_pegawai']
        divisi_id = request.form['divisi_id']
        username = request.form['username']
        password = request.form['password']

        # Simpan data pegawai baru
        pegawai = Pegawai(
            nama_pegawai=nama_pegawai,
            divisi_id=divisi_id,
            username=username,
            password=password,  # atau hashed_password jika menggunakan hashing
        )
        db.session.add(pegawai)
        db.session.commit()

        return redirect(url_for('divisi_pegawai'))  # Redirect ke halaman yang diinginkan

    # Ambil data divisi dari database
    divisi_list = Divisi.query.all()

    # Debugging: print divisi_list untuk memastikan ada data
    print("Divisi List:", divisi_list)  # Pastikan ini mencetak daftar divisi

    return render_template('tambah_pegawai.html', divisi_list=divisi_list)

# Route Divisi_presentasi_pegawai
@app.route('/presensi_pegawai')
def presensi_pegawai():
    return render_template('divisi_presensi_pegawai.html') 

# Route Divisi_konfigurasi_kamera_presensi
@app.route('/divisi_kamera_presensi', methods=['GET', 'POST'])
def divisi_kamera_presensi():
    if request.method == 'POST':
        try:
            # Ambil data dari form
            nama_kamera = request.form.get('nama_kamera')
            role_kamera = request.form.get('role_kamera').lower()
            ip_rtsp = request.form.get('ip_rtsp')
            jam_mulai_kedatangan = request.form.get('jam_mulai_kedatangan')
            jam_berakhir_kedatangan = request.form.get('jam_berakhir_kedatangan')
            jam_mulai_pulang = request.form.get('jam_mulai_pulang')
            jam_berakhir_pulang = request.form.get('jam_berakhir_pulang')

            # Validasi Role Kamera hanya boleh 'in' atau 'out'
            if role_kamera not in ['in', 'out']:
                flash("Role Kamera harus 'in' atau 'out'", "danger")
                return redirect(url_for('divisi_kamera_presensi'))

            # Konversi jam ke format time
            jam_mulai_kedatangan = datetime.strptime(jam_mulai_kedatangan, "%H:%M").time()
            jam_berakhir_kedatangan = datetime.strptime(jam_berakhir_kedatangan, "%H:%M").time()
            jam_mulai_pulang = datetime.strptime(jam_mulai_pulang, "%H:%M").time()
            jam_berakhir_pulang = datetime.strptime(jam_berakhir_pulang, "%H:%M").time()

            # Simpan ke database
            kamera_baru = KonfigurasiKamerapresensi(
                nama_kamera=nama_kamera,
                role_kamera=RoleKamera(role_kamera),
                ip_rtsp=ip_rtsp,
                jam_mulai_kedatangan=jam_mulai_kedatangan,
                jam_berakhir_kedatangan=jam_berakhir_kedatangan,
                jam_mulai_pulang=jam_mulai_pulang,
                jam_berakhir_pulang=jam_berakhir_pulang
            )
            db.session.add(kamera_baru)
            db.session.commit()
            flash("Kamera Presensi berhasil ditambahkan!", "success")

        except Exception as e:
            db.session.rollback()
            flash(f"Error: {str(e)}", "danger")

        return redirect(url_for('divisi_kamera_presensi'))

    # Jika method GET, ambil semua data dari database
    kamera_list = KonfigurasiKamerapresensi.query.all()
    return render_template('divisi_kamera_presensi.html', kamera_list=kamera_list)

# Route edit konfigurasi kamera presensi
@app.route('/edit_kamera/<int:kamera_id>', methods=['POST'])
def edit_kamera(kamera_id):
    kamera = KonfigurasiKamerapresensi.query.get(kamera_id)
    if kamera:
        kamera.nama_kamera = request.form['nama_kamera']
        kamera.ip_rtsp = request.form['ip_rtsp']
        kamera.jam_mulai_kedatangan = request.form['jam_mulai_kedatangan']
        kamera.jam_berakhir_kedatangan = request.form['jam_berakhir_kedatangan']
        kamera.jam_mulai_pulang = request.form['jam_mulai_pulang']
        kamera.jam_berakhir_pulang = request.form['jam_berakhir_pulang']
        db.session.commit()
    return redirect(url_for('divisi_kamera_presensi'))

# Route delete konfigurasi kamera presensi
@app.route('/hapus_kamera/<int:kamera_id>', methods=['POST'])
def hapus_kamera(kamera_id):
    try:
        kamera = KonfigurasiKamerapresensi.query.get(kamera_id)
        if not kamera:
            flash("Kamera tidak ditemukan!", "danger")
            return redirect(url_for('divisi_kamera_presensi'))

        db.session.delete(kamera)
        db.session.commit()
        flash("Kamera berhasil dihapus!", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Error: {str(e)}", "danger")

    return redirect(url_for('divisi_kamera_presensi'))


# Route Divisi_konfigurasi_kamera pelacakan kinerja
@app.route('/divisi_kamera_pelacakan', methods=['GET', 'POST'])
def divisi_kamera_pelacakan():
    if request.method == 'POST':
        try:
            nama_kamera = request.form.get('nama_kamera')
            ip_rtsp = request.form.get('ip_rtsp')

            if not nama_kamera or not ip_rtsp:
                flash("Nama Kamera dan IP RTSP harus diisi!", "danger")
                return redirect(url_for('divisi_kamera_pelacakan'))

            kamera_baru = KonfigurasiKamerapelacakankerja(nama_kamera=nama_kamera, ip_rtsp=ip_rtsp)
            db.session.add(kamera_baru)
            db.session.commit()
            flash("Kamera Pelacakan berhasil ditambahkan!", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error: {str(e)}", "danger")

        return redirect(url_for('divisi_kamera_pelacakan'))

    kamerapelacakan_list = KonfigurasiKamerapelacakankerja.query.all()
    return render_template('divisi_kamera_pelacakan.html', kamerapelacakan_list=kamerapelacakan_list)


# Route edit konfigurasi kamera pelacakan
@app.route('/edit_kamerapelacakan/<int:kamera_id>', methods=['POST'])
def edit_kamerapelacakan(kamera_id):
    kamera = KonfigurasiKamerapelacakankerja.query.get(kamera_id)
    if kamera:
        kamera.nama_kamera = request.form['nama_kamera']
        kamera.ip_rtsp = request.form['ip_rtsp']
        db.session.commit()
    return redirect(url_for('divisi_kamera_pelacakan'))

# Route delete konfigurasi kamera pelacakan
@app.route('/hapus_kamerapelacakan/<int:kamera_id>', methods=['POST'])
def hapus_kamerapelacakan(kamera_id):
    try:
        kamera = KonfigurasiKamerapelacakankerja.query.get(kamera_id)
        if not kamera:
            flash("Kamera tidak ditemukan!", "danger")
            return redirect(url_for('divisi_kamera_pelacakan'))

        db.session.delete(kamera)
        db.session.commit()
        flash("Kamera berhasil dihapus!", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Error: {str(e)}", "danger")

    return redirect(url_for('divisi_kamera_pelacakan'))


# Route Dashboard Pegawai
@app.route('/pegawai_dashboard')
def pegawai_dashboard():
    if 'user_id' not in session or session['role'] != 'pegawai':
        return redirect(url_for('login'))  # Jika belum login atau bukan pegawai, redirect ke login
    return render_template('pegawai_dashboard.html', username=session['username'])

#Route Kamera Presensi
@app.route('/admin_kamera_presensi_realtime')
def admin_kamera_presensi_realtime():
    return render_template('admin_kamera_presensi_realtime.html')

#Route Kamera Pelacakan Kinerja
@app.route('/admin_kamera_pelacakan_realtime')
def admin_kamera_pelacakan_realtime():
    return render_template('admin_kamera_pelacakan_realtime.html')

#Route Presensi Pegawai
@app.route('/admin_kamera_presensi')
def admin_kamera_presensi():
    return render_template('admin_presensi_pegawai.html')

#Route Kamera Lama Kerja
@app.route('/admin_lama_kerja')
def admin_lama_kerja():
    return render_template('admin_lama_kerja.html')

# Membuat tabel secara otomatis dan menambah data superadmin pertama kali
with app.app_context():
    db.create_all()

    # Cek apakah superadmin sudah ada di database, jika belum tambahkan
    superadmin_exists = Superadmin.query.filter_by(username='superadmin').first()
    if not superadmin_exists:
        # Menambahkan superadmin pertama kali
       # Menambahkan superadmin pertama kali
        new_superadmin = Superadmin(username='superadmin', password='superadmin123', role='superadmin')
        db.session.add(new_superadmin)
        db.session.commit()


if __name__ == '__main__':
    app.run(debug=True)



