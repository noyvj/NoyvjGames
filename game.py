from js import document, setTimeout
from pyodide.ffi import create_proxy

# --- state ---
resource_count = 0


def update_display():
    document.getElementById("resource-count").innerText = str(resource_count)


def clear_pressed(button):
    def _clear(*args):
        button.classList.remove("pressed")
    setTimeout(create_proxy(_clear), 120)


def on_click(event):
    global resource_count
    resource_count += 1
    update_display()

    button = document.getElementById("click-button")
    button.classList.add("pressed")
    clear_pressed(button)


def setup():
    button = document.getElementById("click-button")
    button.innerText = "Mine Iron"
    button.disabled = False
    button.addEventListener("click", create_proxy(on_click))
    update_display()


setup()
