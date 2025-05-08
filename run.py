import os
import sys
import subprocess
import platform
import shutil
import venv

def is_venv():
    return (hasattr(sys, 'real_prefix') or 
            (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix))

def setup():
    python_exe = None
    venv_dir = "venv"
    
    if is_venv():
        if platform.system() == "Windows":
            return os.path.join(sys.prefix, "Scripts", "python.exe")
        return os.path.join(sys.prefix, "bin", "python")
    
    if os.path.exists(venv_dir):
        try:
            shutil.rmtree(venv_dir)
        except:
            if platform.system() == "Windows":
                python_exe = os.path.join(venv_dir, "Scripts", "python.exe")
            else:
                python_exe = os.path.join(venv_dir, "bin", "python")
                
            if os.path.exists(python_exe):
                return python_exe
            else:
                print("Python не найден в существующем окружении")
                print("Необходимо закрыть процессы виртуального окружения")
                print("Или активировать вручную:")
                if platform.system() == "Windows":
                    print("   .\\venv\\Scripts\\activate")
                else:
                    print("   source venv/bin/activate")
                sys.exit(1)
    
    venv.create(venv_dir, with_pip=True)
    
    if platform.system() == "Windows":
        return os.path.join(venv_dir, "Scripts", "python.exe")
    return os.path.join(venv_dir, "bin", "python")

def install_deps(python):
    try:
        subprocess.check_call([python, "-m", "pip", "install", "--upgrade", "pip"])
    except:
        try:
            subprocess.check_call([python, "-m", "ensurepip"])
            subprocess.check_call([python, "-m", "pip", "install", "--upgrade", "pip"])
        except Exception as e:
            print(f"Ошибка pip: {e}")
            sys.exit(1)
    
    try:
        subprocess.check_call([
            python, "-m", "pip", "install", 
            "torch==2.5.1", "torchvision", "torchaudio", 
            "--index-url", "https://download.pytorch.org/whl/cu121"
        ])
    except:
        subprocess.check_call([
            python, "-m", "pip", "install", 
            "torch==2.5.1", "torchvision", "torchaudio"
        ])
    
    with open("requirements.txt", "r") as f:
        reqs = [l for l in f.read().splitlines() if not l.startswith("torch")]
    
    with open("temp_reqs.txt", "w") as f:
        f.write("\n".join(reqs))
    
    subprocess.check_call([python, "-m", "pip", "install", "-r", "temp_reqs.txt"])
    
    if os.path.exists("temp_reqs.txt"):
        os.remove("temp_reqs.txt")

def setup_db():
    db_paths = [
        os.path.join("database", "bot_content.db"),
        os.path.join(os.getcwd(), "database", "bot_content.db")
    ]
    
    for path in db_paths:
        if os.path.exists(path):
            return path
    
    db_dir = os.path.join(os.getcwd(), "database")
    os.makedirs(db_dir, exist_ok=True)
    return os.path.join(db_dir, "bot_content.db")

def setup_env():
    if not os.path.exists(".env"):
        if os.path.exists(".env_example"):
            shutil.copy(".env_example", ".env")
            
            token = input("Токен бота (Enter для пропуска): ").strip()
            admin = input("ID админа (Enter для пропуска): ").strip()
            db_path = setup_db()
            
            with open(".env", "r") as f:
                env = f.read()
            
            if token:
                env = env.replace("BOT_TOKEN=", f"BOT_TOKEN={token}")
            if admin:
                env = env.replace("TG_BOT_ADMIN_ID=", f"TG_BOT_ADMIN_ID={admin}")
            
            if "DB_PATH=" in env:
                env = env.replace("DB_PATH=", f"DB_PATH={db_path}")
            else:
                env += f"\nDB_PATH={db_path}"
            
            with open(".env", "w") as f:
                f.write(env)
        else:
            print("Файл .env_example не найден")
    else:
        with open(".env", "r") as f:
            env = f.read()
        
        if "DB_PATH=" not in env or "duckie.db" in env:
            db_path = setup_db()
            
            if "DB_PATH=" in env:
                env = env.replace("DB_PATH=", f"DB_PATH={db_path}")
            else:
                env += f"\nDB_PATH={db_path}"
            
            with open(".env", "w") as f:
                f.write(env)

def main():
    python = setup()
    
    if not is_venv() or input("Установить зависимости? (д/н): ").strip().lower() != 'н':
        try:
            install_deps(python)
        except Exception as e:
            print(f"Ошибка установки: {e}")
    
    setup_env()
    
    if input("Запустить бота? (д/н): ").strip().lower() == 'д':
        try:
            subprocess.check_call([python, "bot.py"])
        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"Ошибка запуска: {e}")
    else:
        if platform.system() == "Windows":
            print("Запуск: venv\\Scripts\\python bot.py")
        else:
            print("Запуск: venv/bin/python bot.py")

if __name__ == "__main__":
    main() 