import os
import time
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

SVTAV1_PRESETS = {
    "ultrafast": "12", "superfast": "11", "veryfast": "10",
    "faster": "9", "fast": "8", "medium": "6",
    "slow": "4", "slower": "3", "veryslow": "2"
}

VP_CPU_MAP = {
    "ultrafast": "8", "superfast": "7", "veryfast": "6",
    "faster": "5", "fast": "4", "medium": "2",
    "slow": "1", "slower": "0", "veryslow": "0"
}


class MatroskaVideoCompressorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Matroska Video Compressor")
        self.root.geometry("600x590")
        self.root.resizable(False, False)

        self.input_file = ""
        self.output_file = ""

        self.current_process = None
        self.is_cancelled = False

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.create_menu()
        self.create_interface()


    def create_menu(self):
        menu_bar = tk.Menu(self.root)
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Open uncompressed video...", command=self.select_input_file)
        file_menu.add_command(label="Set destination...", command=self.select_output_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        menu_bar.add_cascade(label="File", menu=file_menu)

        action_menu = tk.Menu(menu_bar, tearoff=0)
        action_menu.add_command(label="Start Compression", command=self.open_parameters_window)
        menu_bar.add_cascade(label="Action", menu=action_menu)
        self.root.config(menu=menu_bar)

    def create_interface(self):
        file_frame = ttk.LabelFrame(self.root, text=" File Management ", padding=10)
        file_frame.pack(fill="x", padx=15, pady=10)

        ttk.Label(file_frame, text="Input Video:").grid(row=0, column=0, sticky="w", pady=5)
        self.input_entry = ttk.Entry(file_frame, width=50, state="readonly")
        self.input_entry.grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="Browse...", command=self.select_input_file).grid(row=0, column=2, padx=5, pady=5)

        ttk.Label(file_frame, text="Output (.mkv):").grid(row=1, column=0, sticky="w", pady=5)
        self.output_entry = ttk.Entry(file_frame, width=50, state="readonly")
        self.output_entry.grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="Save as...", command=self.select_output_file).grid(row=1, column=2, padx=5, pady=5)

        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(pady=10)

        self.btn_compress = ttk.Button(btn_frame, text="ACTIVATE COMPRESSION", command=self.open_parameters_window)
        self.btn_compress.pack(side="left", padx=5)

        self.btn_cancel = ttk.Button(btn_frame, text="CANCEL COMPRESSION", command=self.cancel_compression,
                                     state="disabled")
        self.btn_cancel.pack(side="left", padx=5)

        progress_frame = ttk.LabelFrame(self.root, text=" Task Status ", padding=10)
        progress_frame.pack(fill="x", padx=15, pady=5)

        self.lbl_status = ttk.Label(progress_frame, text="Status: Ready / Idle", font=("Helvetica", 10, "bold"))
        self.lbl_status.pack(anchor="w", pady=2)

        self.lbl_eta = ttk.Label(progress_frame, text="Time remaining: --", font=("Helvetica", 9, "italic"))
        self.lbl_eta.pack(anchor="w", pady=2)

        self.progress_bar = ttk.Progressbar(progress_frame, mode="determinate", length=540, maximum=100)
        self.progress_bar.pack(fill="x", pady=5)

        self.metrics_frame = ttk.LabelFrame(self.root, text=" Compression Metrics (Results) ", padding=10)
        self.metrics_frame.pack(fill="both", expand=True, padx=15, pady=10)

        self.lbl_time = ttk.Label(self.metrics_frame, text="Compression duration: --")
        self.lbl_time.pack(anchor="w", pady=2)
        self.lbl_speed_fps = ttk.Label(self.metrics_frame, text="Average encoding speed: --")
        self.lbl_speed_fps.pack(anchor="w", pady=2)
        self.lbl_size_in = ttk.Label(self.metrics_frame, text="Original file size: --")
        self.lbl_size_in.pack(anchor="w", pady=2)
        self.lbl_size_out = ttk.Label(self.metrics_frame, text="Compressed file size: --")
        self.lbl_size_out.pack(anchor="w", pady=2)
        self.lbl_bitrate = ttk.Label(self.metrics_frame, text="Final output bitrate: --")
        self.lbl_bitrate.pack(anchor="w", pady=2)
        self.lbl_ratio = ttk.Label(self.metrics_frame, text="Compression ratio (%): --")
        self.lbl_ratio.pack(anchor="w", pady=2)
        self.lbl_savings = ttk.Label(self.metrics_frame, text="Total space saved: --")
        self.lbl_savings.pack(anchor="w", pady=2)

    def select_input_file(self):
        if self.current_process is not None:
            messagebox.showwarning("Locked", "You cannot change the input file while compression is active.")
            return

        path = filedialog.askopenfilename(
            title="Select Uncompressed Video",
            filetypes=[("Video Files", "*.avi *.mov *.mp4 *.mkv *.yuv *.y4m")]
        )
        if path:
            self.input_file = path
            self.input_entry.config(state="normal")
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, path)
            self.input_entry.config(state="readonly")

    def select_output_file(self):
        if self.current_process is not None:
            messagebox.showwarning("Locked", "You cannot change the destination path while compression is active.")
            return

        path = filedialog.asksaveasfilename(
            title="Set Output Destination",
            defaultextension=".mkv",
            filetypes=[("Matroska Container", "*.mkv")]
        )
        if path:
            self.output_file = path
            self.output_entry.config(state="normal")
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, path)
            self.output_entry.config(state="readonly")

    def open_parameters_window(self):
        if self.current_process is not None:
            messagebox.showwarning("Process Running", "A compression process is already active!")
            return

        if not self.input_file or not self.output_file:
            messagebox.showwarning("Warning", "You must select both input and output files first!")
            return

        param_window = tk.Toplevel(self.root)
        param_window.title("Advanced Compression Parameters")
        param_window.geometry("460x400")
        param_window.resizable(False, False)
        param_window.transient(self.root)
        param_window.grab_set()

        param_window.columnconfigure(1, weight=1)

        ttk.Label(param_window, text="Video Codec:").grid(row=0, column=0, sticky="w", padx=20, pady=8)
        v_codec_cb = ttk.Combobox(param_window, values=[
            "libx264 (H.264)",
            "libx265 (H.265)",
            "libvpx-vp9 (VP9)",
            "libsvtav1 (AV1 - Next-Gen)",
            "libvpx (VP8 - Legacy)"
        ], state="readonly")
        v_codec_cb.grid(row=0, column=1, sticky="ew", padx=20, pady=8)
        v_codec_cb.current(0)

        ttk.Label(param_window, text="Encoder Preset:").grid(row=1, column=0, sticky="w", padx=20, pady=8)
        preset_cb = ttk.Combobox(param_window,
                                 values=["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow",
                                         "slower", "veryslow"], state="readonly")
        preset_cb.grid(row=1, column=1, sticky="ew", padx=20, pady=8)
        preset_cb.current(5)

        ttk.Label(param_window, text="Quality (CRF Scale):").grid(row=2, column=0, sticky="w", padx=20, pady=8)
        crf_scale = tk.Scale(param_window, from_=0, to=51, orient="horizontal")
        crf_scale.grid(row=2, column=1, sticky="ew", padx=20, pady=8)
        crf_scale.set(23)

        def on_codec_change(event):
            selected_codec = v_codec_cb.get()
            if "libx264" in selected_codec:
                crf_scale.config(to=51)
                crf_scale.set(23)
            elif "libx265" in selected_codec:
                crf_scale.config(to=51)
                crf_scale.set(28)
            elif "libvpx-vp9" in selected_codec:
                crf_scale.config(to=63)
                crf_scale.set(31)
            elif "libsvtav1" in selected_codec:
                crf_scale.config(to=63)
                crf_scale.set(32)
            elif "libvpx" in selected_codec and "vp9" not in selected_codec:
                crf_scale.config(to=63)
                crf_scale.set(10)

        v_codec_cb.bind("<<ComboboxSelected>>", on_codec_change)

        ttk.Label(param_window, text="Scale Resolution:").grid(row=3, column=0, sticky="w", padx=20, pady=8)
        res_cb = ttk.Combobox(param_window, values=[
            "Original (No scale)",
            "7680x4320 (8K UHD)",
            "3840x2160 (4K UHD)",
            "2560x1440 (2K QHD)",
            "1920x1080 (Full HD)",
            "1280x720 (HD)",
            "854x480 (SD)"
        ], state="readonly")
        res_cb.grid(row=3, column=1, sticky="ew", padx=20, pady=8)
        res_cb.current(0)

        ttk.Label(param_window, text="Frame Rate (FPS):").grid(row=4, column=0, sticky="w", padx=20, pady=8)
        fps_cb = ttk.Combobox(param_window, values=["Original (Keep)", "60 fps", "30 fps", "24 fps"], state="readonly")
        fps_cb.grid(row=4, column=1, sticky="ew", padx=20, pady=8)
        fps_cb.current(0)

        ttk.Label(param_window, text="Audio Codec:").grid(row=5, column=0, sticky="w", padx=20, pady=8)
        a_codec_cb = ttk.Combobox(param_window, values=[
            "aac (AAC)",
            "libopus (Opus)",
            "libmp3lame (MP3)",
            "flac (FLAC Lossless)",
            "ac3 (Dolby AC-3)",
            "copy (No compression)",
            "mute (No audio)"
        ], state="readonly")
        a_codec_cb.grid(row=5, column=1, sticky="ew", padx=20, pady=8)
        a_codec_cb.current(0)

        def confirm_and_start():
            v_codec = v_codec_cb.get().split(" ")[0]
            preset_val = preset_cb.get()
            crf_val = str(crf_scale.get())
            res_val = res_cb.get()
            fps_val = fps_cb.get()
            a_codec = a_codec_cb.get().split(" ")[0]

            param_window.destroy()

            threading.Thread(
                target=self.execute_compression,
                args=(v_codec, preset_val, crf_val, res_val, fps_val, a_codec),
                daemon=True
            ).start()

        ttk.Button(param_window, text="CONFIRM & START", command=confirm_and_start).grid(row=6, column=0, columnspan=2,
                                                                                         pady=15)

    def get_video_duration(self, file_path):
        cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            file_path
        ]
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                    startupinfo=startupinfo)
            return float(result.stdout.strip())
        except:
            return None

    def has_audio_stream(self, file_path):
        cmd = [
            'ffprobe', '-v', 'error',
            '-select_streams', 'a',
            '-show_entries', 'stream=codec_name',
            '-of', 'csv=p=0',
            file_path
        ]
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                    startupinfo=startupinfo)
            return bool(result.stdout.strip())
        except:
            return False

    def parse_time_to_seconds(self, time_str):
        try:
            parts = time_str.split(':')
            if len(parts) == 3:
                h, m, s = parts
                return int(h) * 3600 + int(m) * 60 + float(s)
        except:
            pass
        return 0

    def update_gui_progress(self, percentage, eta_text):
        if not self.is_cancelled:
            self.progress_bar['value'] = percentage
            self.lbl_status.config(text=f"Status: COMPRESSING... ({percentage:.1f}%)", foreground="orange")
            self.lbl_eta.config(text=eta_text)

    def cancel_compression(self):
        if self.current_process:
            if messagebox.askyesno("Confirm Interruption",
                                   "Are you sure you want to stop the current compression process?"):
                self.is_cancelled = True
                try:
                    self.current_process.terminate()
                except:
                    pass

                self.progress_bar['value'] = 0
                self.lbl_status.config(text="Status: CANCELLED BY USER", foreground="red")
                self.lbl_eta.config(text="Time remaining: Process aborted")
                self.btn_compress.config(state="normal")
                self.btn_cancel.config(state="disabled")
                self.current_process = None

    def execute_compression(self, v_codec, preset, crf, resolution, fps, a_codec):
        self.btn_compress.config(state="disabled")
        self.btn_cancel.config(state="normal")

        self.lbl_status.config(text="Status: Analyzing video metadata...", foreground="blue")
        self.lbl_eta.config(text="Time remaining: Calculating...")
        self.progress_bar['value'] = 0
        self.is_cancelled = False

        total_duration = self.get_video_duration(self.input_file)
        if self.is_cancelled: return

        has_audio = self.has_audio_stream(self.input_file)
        audio_warning_triggered = False
        if not has_audio and a_codec != "mute":
            a_codec = "mute"
            audio_warning_triggered = True

        crf_int = int(crf)
        if v_codec in ["libx264", "libx265"]:
            crf_int = min(51, max(0, crf_int))
        else:
            crf_int = min(63, max(0, crf_int))
        crf = str(crf_int)

        status_text = "Status: COMPRESSING... (0.0%)"
        if audio_warning_triggered:
            status_text += " [No Audio Detected - Mute Forced]"

        self.lbl_status.config(text=status_text, foreground="orange")
        start_time = time.time()

        log_path = "ffmpeg_debug.log"
        try:
            log_file = open(log_path, "w", encoding="utf-8")
        except:
            log_file = subprocess.DEVNULL

        command = [
            'ffmpeg', '-y',
            '-i', self.input_file,
            '-progress', 'pipe:1'
        ]

        command.extend(['-c:v', v_codec])

        if v_codec == "libsvtav1":
            mapped_preset = SVTAV1_PRESETS.get(preset, "6")
            command.extend(['-preset', mapped_preset])
            command.extend(['-pix_fmt', 'yuv420p10le'])
            command.extend(['-crf', crf])
        elif v_codec in ["libvpx", "libvpx-vp9"]:
            cpu_val = VP_CPU_MAP.get(preset, "2")
            if v_codec == "libvpx":
                cpu_val = str(min(5, int(cpu_val)))
            command.extend(['-cpu-used', cpu_val])
            if preset in ["ultrafast", "superfast", "veryfast"]:
                command.extend(['-deadline', 'realtime'])
            else:
                command.extend(['-deadline', 'good'])
            command.extend(['-pix_fmt', 'yuv420p'])
            command.extend(['-b:v', '0', '-crf', crf])
        else:
            command.extend(['-preset', preset])
            command.extend(['-pix_fmt', 'yuv420p'])
            command.extend(['-crf', crf])

        if "7680x4320" in resolution:
            command.extend(['-vf', 'scale=7680:-2'])
        elif "3840x2160" in resolution:
            command.extend(['-vf', 'scale=3840:-2'])
        elif "2560x1440" in resolution:
            command.extend(['-vf', 'scale=2560:-2'])
        elif "1920x1080" in resolution:
            command.extend(['-vf', 'scale=1920:-2'])
        elif "1280x720" in resolution:
            command.extend(['-vf', 'scale=1280:-2'])
        elif "854x480" in resolution:
            command.extend(['-vf', 'scale=854:-2'])

        if "60 fps" in fps:
            command.extend(['-r', '60'])
        elif "30 fps" in fps:
            command.extend(['-r', '30'])
        elif "24 fps" in fps:
            command.extend(['-r', '24'])

        if "copy" in a_codec:
            command.extend(['-c:a', 'copy'])
        elif "mute" in a_codec:
            command.extend(['-an'])
        else:
            command.extend(['-c:a', a_codec])

        command.append(self.output_file)

        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            self.current_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=log_file,
                text=True,
                startupinfo=startupinfo
            )

            total_frames = 0
            last_ffmpeg_bitrate = "N/A"

            for line in self.current_process.stdout:
                if self.is_cancelled:
                    if log_file and log_file != subprocess.DEVNULL: log_file.close()
                    return

                if "frame=" in line:
                    try:
                        total_frames = int(line.split("=")[1].strip())
                    except:
                        pass

                if "bitrate=" in line:
                    last_ffmpeg_bitrate = line.split("=")[1].strip()

                if "out_time=" in line:
                    time_str = line.split("=")[1].strip()
                    if total_duration and total_duration > 0:
                        current_seconds = self.parse_time_to_seconds(time_str)
                        percentage = (current_seconds / total_duration) * 100
                        percentage = min(100.0, max(0.0, percentage))

                        elapsed_time = time.time() - start_time
                        if current_seconds > 0:
                            remaining_seconds = (elapsed_time / current_seconds) * (total_duration - current_seconds)
                            remaining_seconds = max(0, remaining_seconds)
                            r_mins, r_secs = divmod(int(remaining_seconds), 60)
                            r_hrs, r_mins = divmod(r_mins, 60)

                            if r_hrs > 0:
                                eta_str = f"Time remaining: about {r_hrs}h {r_mins}m {r_secs}s"
                            else:
                                eta_str = f"Time remaining: about {r_mins}m {r_secs}s"
                        else:
                            eta_str = "Time remaining: Calculating..."

                        self.root.after(0, self.update_gui_progress, percentage, eta_str)

            self.current_process.wait()
            if log_file and log_file != subprocess.DEVNULL:
                log_file.close()

            if self.is_cancelled:
                return

            if self.current_process.returncode != 0:
                raise Exception("FFmpeg internal error. Please inspect the log file.")

            end_time = time.time()
            duration = end_time - start_time

            if duration >= 3600:
                h = int(duration // 3600)
                m = int((duration % 3600) // 60)
                s = duration % 60
                duration_text = f"{h}h {m}m {s:.2f}s"
            elif duration >= 60:
                m = int(duration // 60)
                s = duration % 60
                duration_text = f"{m}m {s:.2f}s"
            else:
                duration_text = f"{duration:.2f} seconds"

            size_in = os.path.getsize(self.input_file) / (1024 * 1024)
            size_out = os.path.getsize(self.output_file) / (1024 * 1024)
            savings = size_in - size_out
            compression_ratio = (size_out / size_in) * 100
            reduced_by = 100 - compression_ratio
            avg_fps = total_frames / duration if duration > 0 else 0

            self.progress_bar['value'] = 100
            self.lbl_status.config(text="Status: SUCCESS / COMPRESSION COMPLETED", foreground="green")
            self.lbl_eta.config(text="Time remaining: Finished!")
            self.btn_compress.config(state="normal")
            self.btn_cancel.config(state="disabled")
            self.current_process = None

            self.lbl_time.config(text=f"Compression duration: {duration_text}")
            self.lbl_speed_fps.config(text=f"Average encoding speed: {avg_fps:.2f} FPS")
            self.lbl_size_in.config(text=f"Original file size: {size_in:.2f} MB")
            self.lbl_size_out.config(text=f"Compressed file size: {size_out:.2f} MB")
            self.lbl_bitrate.config(text=f"Final output bitrate: {last_ffmpeg_bitrate}")
            self.lbl_ratio.config(text=f"Compression ratio: {compression_ratio:.1f}% of original")
            self.lbl_savings.config(text=f"Total space saved: {savings:.2f} MB (Reduced by {reduced_by:.1f}%)")

            messagebox.showinfo("Success", "Video successfully compressed!")

        except Exception as e:
            if log_file and log_file != subprocess.DEVNULL:
                try:
                    log_file.close()
                except:
                    pass

            if not self.is_cancelled:
                self.progress_bar['value'] = 0
                self.lbl_status.config(text="Status: ERROR OCCURRED", foreground="red")
                self.lbl_eta.config(text="Time remaining: N/A")
                self.btn_compress.config(state="normal")
                self.btn_cancel.config(state="disabled")
                self.current_process = None

                messagebox.showerror(
                    "Error",
                    f"Compression failed!\n\n"
                    f"A detailed error log has been generated at '{log_path}'.\n"
                    f"Please inspect it to see the technical reason.\n\n"
                    f"Exception summary: {str(e)}"
                )

    def on_closing(self):
        if self.current_process is not None:
            if messagebox.askyesno("Warning: Process Active",
                                   "A video compression is currently running!\n\n"
                                   "Exiting will forcefully terminate the process.\n"
                                   "Are you sure you want to quit?"):
                self.is_cancelled = True
                try:
                    self.current_process.terminate()
                    self.current_process.wait()
                except:
                    pass
                self.root.destroy()
        else:
            self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = MatroskaVideoCompressorApp(root)
    root.mainloop()