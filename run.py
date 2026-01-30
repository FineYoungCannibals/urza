# /run.py
# # This CLI client is only used to run the shell to authenticate a TG User
from urza.cli.shell import UrzaShell

def main():
    """Launch URZA interactive shell"""
    # Start shell
    app = UrzaShell()
    app.cmdloop()


if __name__ == '__main__':
    main()