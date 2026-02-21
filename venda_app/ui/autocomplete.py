import tkinter as tk
import customtkinter as ctk

class AutocompleteEntry(ctk.CTkEntry):
    """
    Entry com dropdown de sugestões.
    - provider(query) -> lista de rows (dict-like) com keys:
      variant_sku, product_name, attr_name, variant_value
    """

    def __init__(self, master, provider, on_select=None, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.provider = provider
        self.on_select = on_select

        self._popup = None
        self._listbox = None
        self._items = []

        self.bind("<KeyRelease>", self._on_keyrelease)
        self.bind("<Down>", self._focus_list)
        self.bind("<Return>", self._accept_first)
        self.bind("<Escape>", lambda e: self._hide())

        # fecha ao perder foco (com um pequeno delay pra permitir click)
        self.bind("<FocusOut>", lambda e: self.after(120, self._hide))

    def _on_keyrelease(self, event):
        # ignora teclas de navegação
        if event.keysym in ("Up", "Down", "Return", "Escape", "Tab"):
            return

        q = self.get().strip()
        if len(q) < 1:
            self._hide()
            return

        self._items = self.provider(q) or []
        if not self._items:
            self._hide()
            return

        self._show()

    def _show(self):
        if self._popup is None or not self._popup.winfo_exists():
            self._popup = tk.Toplevel(self)
            self._popup.wm_overrideredirect(True)
            self._popup.attributes("-topmost", True)

            self._listbox = tk.Listbox(self._popup, activestyle="none")
            self._listbox.pack(fill="both", expand=True)

            self._listbox.bind("<ButtonRelease-1>", self._accept_selected)
            self._listbox.bind("<Return>", self._accept_selected)
            self._listbox.bind("<Escape>", lambda e: self._hide())
            self._listbox.bind("<Up>", self._list_up)
            self._listbox.bind("<Down>", self._list_down)

        # posiciona abaixo do entry
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        w = self.winfo_width()
        self._popup.geometry(f"{max(w, 420)}x220+{x}+{y}")

        # popula listbox
        self._listbox.delete(0, tk.END)
        for r in self._items:
            label = f"{r['variant_sku']}  —  {r['product_name']} ({r['attr_name']}: {r['variant_value']})"
            self._listbox.insert(tk.END, label)

        self._listbox.selection_clear(0, tk.END)
        self._listbox.selection_set(0)
        self._listbox.activate(0)

    def _hide(self):
        if self._popup and self._popup.winfo_exists():
            self._popup.destroy()
        self._popup = None
        self._listbox = None
        self._items = []

    def _focus_list(self, event=None):
        if self._listbox and self._listbox.winfo_exists():
            self._listbox.focus_set()
        return "break"

    def _accept_first(self, event=None):
        if self._items:
            self._apply_item(self._items[0])
            return "break"
        return None

    def _accept_selected(self, event=None):
        if not self._listbox:
            return "break"
        idx = self._listbox.curselection()
        if not idx:
            return "break"
        item = self._items[idx[0]]
        self._apply_item(item)
        return "break"

    def _apply_item(self, item):
        self.delete(0, tk.END)
        self.insert(0, item["variant_sku"])
        self._hide()
        if callable(self.on_select):
            self.on_select(item)

    def _list_up(self, event=None):
        if not self._listbox:
            return "break"
        i = max(0, (self._listbox.curselection()[0] if self._listbox.curselection() else 0) - 1)
        self._listbox.selection_clear(0, tk.END)
        self._listbox.selection_set(i)
        self._listbox.activate(i)
        return "break"

    def _list_down(self, event=None):
        if not self._listbox:
            return "break"
        cur = self._listbox.curselection()[0] if self._listbox.curselection() else 0
        i = min(self._listbox.size() - 1, cur + 1)
        self._listbox.selection_clear(0, tk.END)
        self._listbox.selection_set(i)
        self._listbox.activate(i)
        return "break"