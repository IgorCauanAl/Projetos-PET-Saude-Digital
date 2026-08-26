import customtkinter as ctk
from interface import AplicacaoGUI

if __name__ == "__main__":
    root = ctk.CTk()
    app = AplicacaoGUI(root)

    # Gerencia o evento de fechamento seguro da janela para desligar os listeners do OS
    root.protocol("WM_DELETE_WINDOW", app.fechar_aplicacao)

    # Inicia o loop de eventos da GUI
    root.mainloop()