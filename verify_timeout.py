
from config import Config

def verify():
    options = getattr(Config, 'SQLALCHEMY_ENGINE_OPTIONS', None)
    print(f"SQLALCHEMY_ENGINE_OPTIONS: {options}")
    
    if options and 'connect_args' in options:
        timeout = options['connect_args'].get('timeout')
        print(f"Timeout: {timeout}")
        if timeout == 30:
            print("VERIFICATION SUCCESS: Timeout is set to 30s")
            return
    
    print("VERIFICATION FAILURE: Timeout is not set correctly")

if __name__ == "__main__":
    verify()
