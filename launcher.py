import os
import sys
import subprocess
import tkinter as tk
from tkinter import messagebox, scrolledtext, simpledialog


BASE_DIR = os.path.dirname(__file__)


class LauncherApp:
    def __init__(self, master):
        self.master = master
        master.title('Launcher - Modo Local / Global')

        # Processes we'll manage
        self.processes = {
            'local': None,       # DashboardLocalPython
            'autopilot': None,   # AutopilotService
            'global': None,      # DashboardGlobalPython
            'camera': None       # CameraService
        }

        # Buttons
        self.btn_local = tk.Button(master, text='Modo Local', width=20, command=self.start_local)
        self.btn_local.grid(row=0, column=0, padx=10, pady=10)

        self.btn_global = tk.Button(master, text='Modo Global', width=20, command=self.start_global)
        self.btn_global.grid(row=0, column=1, padx=10, pady=10)

        self.btn_stop = tk.Button(master, text='Detener Todo', width=20, command=self.stop_all)
        self.btn_stop.grid(row=0, column=2, padx=10, pady=10)

        # Log area
        self.log = scrolledtext.ScrolledText(master, width=80, height=15, state='disabled')
        self.log.grid(row=1, column=0, columnspan=3, padx=10, pady=(0,10))

        # Poll child processes periodically to update UI
        self._poll_interval_ms = 1000
        self.master.after(self._poll_interval_ms, self._poll_processes)

    def _log(self, *parts):
        text = ' '.join(str(p) for p in parts)
        self.log.configure(state='normal')
        self.log.insert(tk.END, text + '\n')
        self.log.see(tk.END)
        self.log.configure(state='disabled')

    def _script_path(self, name):
        # helper to get absolute path to a script in the same folder
        return os.path.join(BASE_DIR, name)

    def _start_process(self, key, script_name, args=None):
        if self.processes.get(key) and self.processes[key].poll() is None:
            self._log(f"Proceso '{key}' ya está en ejecución (pid={self.processes[key].pid}).")
            return

        script = self._script_path(script_name)
        if not os.path.exists(script):
            messagebox.showerror('Error', f"No se encontró el script: {script_name}")
            return

        cmd = [sys.executable, script]
        if args:
            cmd += args

        try:
            # Start as a normal subprocess; use cwd so relative imports/resources work.
            p = subprocess.Popen(cmd, cwd=BASE_DIR)
            self.processes[key] = p
            self._log(f"Iniciado '{key}' -> {script_name} (pid={p.pid})")
        except Exception as e:
            messagebox.showerror('Error', f'No se pudo iniciar {script_name}: {e}')
            self._log(f'Error al iniciar {script_name}: {e}')

    def _is_port_in_use(self, port):
        """Return (in_use, pid) if a process is listening on the given TCP port on this host."""
        try:
            out = subprocess.check_output(["netstat", "-ano"], text=True, stderr=subprocess.DEVNULL)
            for line in out.splitlines():
                parts = line.split()
                # lines may vary; typical: Proto  LocalAddress  ForeignAddress  State  PID
                if len(parts) >= 5:
                    local = parts[1]
                    state = parts[3]
                    pid = parts[4]
                    # match :port in local address (IPv4)
                    if f":{port}" in local and state.upper() == 'LISTENING':
                        try:
                            return True, int(pid)
                        except Exception:
                            return True, None
            return False, None
        except Exception:
            return False, None

    def start_local(self):
        # Ensure background services are running first (Autopilot + Camera)
        if not (self.processes.get('autopilot') and self.processes['autopilot'].poll() is None):
            self._start_process('autopilot', 'AutopilotService.py')
        else:
            self._log('AutopilotService ya se estaba ejecutando.')
        # For local mode we do NOT pre-ask connection mode here.
        # The local dashboard will prompt the user to select SIM/ESC when they click the Connect button.
        self._log('Iniciando modo local. El dashboard pedirá modo de conexión al pulsar "Conectar".')

        # If some process is already listening on CameraService default port (9999), do not start another
        in_use, pid = self._is_port_in_use(9999)
        if in_use:
            self._log(f'Puerto 9999 ya en uso (pid={pid}); no se iniciará otra instancia de CameraService.')
        else:
            if not (self.processes.get('camera') and self.processes['camera'].poll() is None):
                self._start_process('camera', 'CameraService.py')
            else:
                self._log('CameraService ya se estaba ejecutando.')

        # Start the local dashboard (it will prompt for SIM/ESC on Connect)
        self._start_process('local', 'DashboardLocalPython.py')

    def start_global(self):
        # Start AutopilotService first, then DashboardGlobalPython
        # If autopilot already running, don't start another
        if not (self.processes.get('autopilot') and self.processes['autopilot'].poll() is None):
            self._start_process('autopilot', 'AutopilotService.py')
        else:
            self._log('AutopilotService ya se estaba ejecutando.')

        # Ask connection mode (simulation vs escenario with COM) before starting services
        mode_args = self._ask_connection_mode()
        if mode_args is None:
            self._log('Inicio de modo global cancelado por el usuario.')
            return

        in_use, pid = self._is_port_in_use(9999)
        if in_use:
            self._log(f'Puerto 9999 ya en uso (pid={pid}); no se iniciará otra instancia de CameraService.')
        else:
            if not (self.processes.get('camera') and self.processes['camera'].poll() is None):
                self._start_process('camera', 'CameraService.py')
            else:
                self._log('CameraService ya se estaba ejecutando.')

        # Start the global dashboard after background services
        # Note: pass mode args to global dashboard as well for consistency
        self._start_process('global', 'DashboardGlobalPython.py', args=mode_args)

    def _ask_connection_mode(self):
        """Ask the user whether to connect to simulation or a real scenario (COM). Returns a list of args or None if cancelled."""
        try:
            respuesta = messagebox.askquestion('Tipo de conexión', "¿Conectar a la SIMULACIÓN?\nSí = Simulación (tcp:127.0.0.1:5763)\nNo = Escenario (Puerto COM)", parent=self.master)
            if respuesta == 'yes':
                return ['--mode', 'sim']
            # Ask COM port
            com_input = simpledialog.askstring('Puerto COM', "Introduce el puerto COM (ej. 'COM3' o solo el número '3'):", parent=self.master)
            if com_input is None:
                return None
            com_input = com_input.strip()
            if com_input == '':
                return None
            com_norm = com_input.replace(' ', '').upper()
            if com_norm.isdigit():
                com_norm = f'COM{com_norm}'
            elif com_norm.startswith('COM') and com_norm[3:].isdigit():
                com_norm = com_norm
            else:
                messagebox.showerror('Puerto COM inválido', f"Puerto COM inválido: '{com_input}'", parent=self.master)
                return None
            return ['--mode', 'esc', '--com', com_norm]
        except Exception:
            return None

    def _terminate_process(self, p, name):
        if not p:
            return
        if p.poll() is not None:
            self._log(f"El proceso '{name}' ya terminó (code={p.returncode}).")
            return

        self._log(f"Terminando proceso '{name}' (pid={p.pid})...")
        try:
            p.terminate()
        except Exception as e:
            self._log(f"Error calling terminate on {name}: {e}")

        try:
            p.wait(timeout=5)
            self._log(f"Proceso '{name}' terminado correctamente (code={p.returncode}).")
        except subprocess.TimeoutExpired:
            self._log(f"Proceso '{name}' no respondió a terminate; forzando kill...")
            try:
                p.kill()
                p.wait(timeout=5)
                self._log(f"Proceso '{name}' forzado a terminar (code={p.returncode}).")
            except Exception as e:
                self._log(f"No se pudo matar el proceso '{name}': {e}")

    def stop_all(self):
        # Terminate the three managed processes if running
        self._log('Iniciando parada de todos los procesos...')
        for key in ('local', 'global', 'autopilot', 'camera'):
            p = self.processes.get(key)
            try:
                self._terminate_process(p, key)
            finally:
                self.processes[key] = None

        self._log('Todos los procesos gestionados han sido solicitados a terminar.')

    def _poll_processes(self):
        # Update UI or log if processes finished
        for key, p in list(self.processes.items()):
            if p and p.poll() is not None:
                # Process finished
                self._log(f"Proceso '{key}' finalizó con código {p.returncode}.")
                self.processes[key] = None

        # schedule next poll
        self.master.after(self._poll_interval_ms, self._poll_processes)


def main():
    root = tk.Tk()
    app = LauncherApp(root)
    root.protocol('WM_DELETE_WINDOW', lambda: (app.stop_all(), root.destroy()))
    root.mainloop()


if __name__ == '__main__':
    main()

