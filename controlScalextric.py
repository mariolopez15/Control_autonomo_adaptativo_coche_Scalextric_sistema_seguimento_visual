import tkinter
import numpy as np
import cv2
import PIL.Image, PIL.ImageTk
import math
import serial
import time
import threading
import json
import csv
import os

arduino = serial.Serial('/dev/ttyACM0', 115200)


def vaciar_buffer():
    arduino.reset_input_buffer()
    arduino.reset_output_buffer()
    while arduino.in_waiting > 0:
        arduino.read()


class Aplicacion:
    def __init__(self):
        self.vc = cv2.VideoCapture(4)
        self.vc.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.vc.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
        self.vc.set(cv2.CAP_PROP_AUTOFOCUS, 0)
        self.width = self.vc.get(cv2.CAP_PROP_FRAME_WIDTH)
        self.height = self.vc.get(cv2.CAP_PROP_FRAME_HEIGHT)
        self.tracker = None  # indica si se inició el tracker
        if not self.vc.isOpened():
            raise ValueError("Unable to open video source", 4)

        self.window = tkinter.Tk()
        self.window.title("Tracking scalextric")
        self.camara = 4
        self.traking = False
        self.meta = None
        self.sectores = None
        self.selectedColor = None
        self.backColor = None
        self.procesado = None
        self.dobleTrayectoria = False
        self.mostrarDerrapes = False
        self.generarDatos = False
        self.vueltas = 0
        self.DataListDerrape = []
        self.DataConjuntoDatos = []
        self.mutex = threading.Lock()
        self.interfaz_running = True
        self.checkTrayectoria = tkinter.IntVar()
        self.checkDerrapes = tkinter.IntVar()
        self.checkDatos = tkinter.IntVar()

        self.stream = Capturador(self.width, self.height)
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

        info_frame = tkinter.Frame(self.window)
        info_frame.pack(pady=0, expand=True)

        # Crear un canvas con el tamaño del video para mostrarlo
        self.video = tkinter.Canvas(info_frame, width=self.stream.width, height=self.stream.height)
        self.video.pack()

        settings_frame = tkinter.Frame(self.window)
        settings_frame.pack(pady=5, expand=True)
        self.button_trayectoria = tkinter.Checkbutton(settings_frame, text="2x Trayectoria", width=25,
                                                      variable=self.checkTrayectoria, command=self.setTrayectoriaCheck)
        self.button_trayectoria.pack(side="left")
        self.button_derrapes = tkinter.Checkbutton(settings_frame, text="Mostrar derrapes", width=25,
                                                   variable=self.checkDerrapes, command=self.setDerrapesCheck)
        self.button_derrapes.pack(side="left")
        self.button_datos = tkinter.Checkbutton(settings_frame, text="Generar datos", width=25,
                                                variable=self.checkDatos, command=self.setDatosCheck)
        self.button_datos.pack(side="left")

        configuration_frame = tkinter.Frame(self.window)
        configuration_frame.pack(pady=5, expand=True)

        color_frame = tkinter.Frame(configuration_frame)
        color_frame.pack(expand=True, side="top", pady=5)

        self.delantera_frame = tkinter.Frame(color_frame)
        # self.delantera_frame.pack(side="left")

        self.color_text = tkinter.Label(self.delantera_frame, text="Etiqueta delantera")
        self.color_text.pack(side="left")
        # self.color_text.pack_forget()

        self.color_rec = tkinter.Canvas(self.delantera_frame, width=15, height=15)
        self.color_rec.pack(side="left", padx=15)

        self.trasera_frame = tkinter.Frame(color_frame)
        # self.trasera_frame.pack(side="left")

        self.color_trasera_text = tkinter.Label(self.trasera_frame, text="Etiqueta trasera")
        self.color_trasera_text.pack(side="left")
        # self.color_text.pack_forget()

        self.color_trasera_rec = tkinter.Canvas(self.trasera_frame, width=15, height=15)
        self.color_trasera_rec.pack(side="right", padx=15)

        # self.color_rec.pack_forget()
        self.button_color = tkinter.Button(configuration_frame, text="Etiqueta delantera", width=17,
                                           command=self.chooseColor)
        self.button_color.pack(side=tkinter.LEFT, expand=True)
        self.button_back_color = tkinter.Button(configuration_frame, text="Etiqueta trasera", width=17,
                                                command=self.chooseBackColor)
        self.button_back_color.pack(side=tkinter.LEFT, expand=True)
        self.button_meta = tkinter.Button(configuration_frame, text="Elegir meta", width=17, command=self.chooseMeta)
        self.button_meta.pack(side=tkinter.LEFT, expand=True)
        self.button_sectores = tkinter.Button(configuration_frame, text="Inidcar sectores", width=17,
                                              command=self.chooseSectores)
        self.button_sectores.pack(side=tkinter.RIGHT, expand=True)

        # Botones para empezar y acabar un tracker
        self.button_start = tkinter.Button(self.window, text="Iniciar seguimiento", width=15, command=self.startTracker)
        self.button_start.pack(side=tkinter.LEFT, expand=True, pady=20)
        self.button_end = tkinter.Button(self.window, text="Parar seguimiento", width=15, command=self.endTracker)
        self.button_end.pack(side=tkinter.LEFT, expand=True, pady=20)
        self.button_start = tkinter.Button(self.window, text="Iniciar carrera", width=15, command=self.iniciarCarrera)
        self.button_start.pack(side=tkinter.LEFT, expand=True, pady=20)
        self.button_start = tkinter.Button(self.window, text="Parar carrera", width=15, command=self.pararCarrera)
        self.button_start.pack(side=tkinter.LEFT, expand=True, pady=20)

        self.getFromJson()

        self.showVideo()
        self.window.mainloop()

    def getFromJson(self):

        if os.path.exists('circuito.json'):
            with open('circuito.json') as file:
                # Load the JSON data into a Python object
                jsonData = json.load(file)
            metaBoolean = jsonData["metaValues"]
            sectorBoolean = jsonData["sectoresValues"]
            colorBoolean = jsonData["colorValues"]
            medicionesBoolean = jsonData["mediciones"]

            if metaBoolean:
                jsonMeta = jsonData["meta"]
                meta = [jsonMeta["inix"], jsonMeta["iniy"], jsonMeta["finx"], jsonMeta["finy"]]
                self.meta = np.array(meta)

            if sectorBoolean:
                jsonSector = jsonData["sectores"]
                sectores = []
                print(jsonSector)
                for sector in jsonSector:
                    print(sector)
                    sectores.append([sector["inix"], sector["iniy"], sector["finx"], sector["finy"]])
                self.sectores = np.array(sectores)

            if colorBoolean:
                jsonColor = jsonData["color"]
                self.selectedColor = [jsonColor["h"], jsonColor["s"], jsonColor["v"]]

                hsvColor = (jsonColor["h"], jsonColor["s"], jsonColor["v"])  # Convert HSV values to OpenCV range
                hsvColor = [[hsvColor]]  # OpenCV expects a 3D array for single pixel conversion
                hsvColor = np.array(hsvColor, dtype=np.uint8)
                rgbColor = cv2.cvtColor(hsvColor, cv2.COLOR_HSV2RGB)[0][0]
                self.color_rec.configure(
                    bg=self.rgbtohex(rgbColor[0], rgbColor[1], rgbColor[2]))  # Muestra el color en la interfaz

                jsonBackColor = jsonData["colorDetras"]
                self.backColor = (jsonBackColor["h"], jsonBackColor["s"], jsonBackColor["v"])

                hsvColor = (
                jsonBackColor["h"], jsonBackColor["s"], jsonBackColor["v"])  # Convert HSV values to OpenCV range
                hsvColor = [[hsvColor]]  # OpenCV expects a 3D array for single pixel conversion
                hsvColor = np.array(hsvColor, dtype=np.uint8)
                rgbColor = cv2.cvtColor(hsvColor, cv2.COLOR_HSV2RGB)[0][0]
                self.color_trasera_rec.configure(
                    bg=self.rgbtohex(rgbColor[0], rgbColor[1], rgbColor[2]))  # Muestra el color en la interfaz
                self.delantera_frame.pack(side="right")
                self.trasera_frame.pack(side="right")

            if medicionesBoolean:
                self.button_datos.select()
                self.generarDatos = True

    def on_close(self):
        self.interfaz_running = False
        self.window.destroy()

    def startTracker(self):
        vaciar_buffer()
        arduino.write(('v' + str(0) + '\n').encode())
        vaciar_buffer()
        if (self.traking == False and self.meta is not None and self.sectores is not None and self.selectedColor is not None and self.backColor is not None):
            self.traking = True
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.salidaVideo = cv2.VideoWriter('output.mp4', fourcc, 30.0, (int(self.width), int(self.height)))
            resul, frame = self.vc.read()
            while (resul == False):
                resul, frame = self.vc.read()
            self.stream.ini_tracker(self.meta, self.sectores, self.selectedColor, self.backColor, frame)

    def endTracker(self):
        vaciar_buffer()
        arduino.write(('v' + str(0) + '\n').encode())
        vaciar_buffer()
        if (self.traking == True):
            self.traking = False
            self.saveValues()
            self.salidaVideo.release()
            self.stream.end_tracker()

    def setTrayectoriaCheck(self):
        estado = self.checkTrayectoria.get()
        if estado == 1:
            self.dobleTrayectoria = True
        if estado == 0:
            self.dobleTrayectoria = False

    def setDerrapesCheck(self):
        estado = self.checkDerrapes.get()
        if estado == 1:
            self.mostrarDerrapes = True
        if estado == 0:
            self.mostrarDerrapes = False

    def setDatosCheck(self):
        estado = self.checkDatos.get()
        if estado == 1:
            self.generarDatos = True
        if estado == 0:
            self.generarDatos = False

    def rgbtohex(self, r, g, b):
        return f'#{r:02x}{g:02x}{b:02x}'

    def chooseColor(self):
        vaciar_buffer()
        arduino.write(('v' + str(0) + '\n').encode())
        vaciar_buffer()
        # Create a new window
        color_window = tkinter.Toplevel()
        color_window.title("Selecciona la marca de seguimiento")

        pic = tkinter.Canvas(color_window, width=self.stream.width, height=self.stream.height)
        pic.pack()

        resul, frame = self.get_frame()
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        if resul:
            imag = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(frame))
            pic.create_image(0, 0, image=imag, anchor=tkinter.NW)

        def get_pixel_color(event):
            x, y = event.x, event.y  # coordenadas donde se pulsó
            f = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            pixel = cv2.cvtColor(f[y:y + 1, x:x + 1], cv2.COLOR_BGR2HSV)
            # Obtiene el color de un pixel
            self.selectedColor = pixel[0][0]  # Color guardado en HSV
            rgbcolor = cv2.cvtColor(pixel, cv2.COLOR_HSV2RGB)[0][0]  # Obtener el color en RGB
            self.color_rec.configure(
                bg=self.rgbtohex(rgbcolor[0], rgbcolor[1], rgbcolor[2]))  # Muestra el color en la interfaz
            print("Selected color: ", self.selectedColor)
            self.delantera_frame.pack(side="right")
            color_window.destroy()

        pic.bind("<Button-1>", get_pixel_color)
        color_window.mainloop()

    def chooseBackColor(self):
        vaciar_buffer()
        arduino.write(('v' + str(0) + '\n').encode())
        vaciar_buffer()
        # Create a new window
        color_window = tkinter.Toplevel()
        color_window.title("Selecciona la marca de seguimiento")

        pic = tkinter.Canvas(color_window, width=self.stream.width, height=self.stream.height)
        pic.pack()

        resul, frame = self.get_frame()
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        if resul:
            imag = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(frame))
            pic.create_image(0, 0, image=imag, anchor=tkinter.NW)

        def get_pixel_color(event):
            x, y = event.x, event.y  # coordenadas donde se pulsó
            f = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            pixel = cv2.cvtColor(f[y:y + 1, x:x + 1], cv2.COLOR_BGR2HSV)
            # Obtiene el color de un pixel
            self.backColor = pixel[0][0]  # Color guardado en HSV
            rgbcolor = cv2.cvtColor(pixel, cv2.COLOR_HSV2RGB)[0][0]  # Obtener el color en RGB
            self.color_trasera_rec.configure(
                bg=self.rgbtohex(rgbcolor[0], rgbcolor[1], rgbcolor[2]))  # Muestra el color en la interfaz
            print("Selected color: ", self.backColor)
            self.trasera_frame.pack(side="right")
            color_window.destroy()

        pic.bind("<Button-1>", get_pixel_color)
        color_window.mainloop()

    def chooseMeta(self):
        self.dibujando = False
        line_init = None
        line_end = None

        # Funcion para dibujar la linea indicada
        def dibujoLinea(event, x, y, flags, param):
            global line_init, line_end
            image = frame.copy()
            if event == cv2.EVENT_LBUTTONDOWN:
                self.dibujando = True
                line_init = (x, y)
                self.meta = [0, 0, 0, 0]
                self.meta[0] = x
                self.meta[1] = y

            if event == cv2.EVENT_MOUSEMOVE:
                if self.dibujando == True:
                    p2 = (x, y)
                    cv2.line(image, (self.meta[0], self.meta[1]), p2, (0, 0, 255), 2)
                    cv2.imshow("Seleccion meta", cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

            elif event == cv2.EVENT_LBUTTONUP:
                self.dibujando = False
                self.meta[2] = x
                self.meta[3] = y
                print(self.meta)

        # Load the image
        resul, frame = self.get_frame()
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Create a window and set the mouse callbackSe crea la ventana con la imagen y se establece el callback
        cv2.namedWindow("Seleccion meta")
        cv2.setMouseCallback("Seleccion meta", dibujoLinea)
        cv2.imshow("Seleccion meta", cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        while True:
            # Si se pulsa x se cierra
            if cv2.getWindowProperty("Seleccion meta", cv2.WND_PROP_VISIBLE) < 1:
                break

            # Tecla pulsada
            key = cv2.waitKey(1) & 0xFF
            # Se sale del bucle si se presiona enter
            if key == ord('\n') or key == ord('\r'):
                break

        cv2.destroyAllWindows()

    def chooseSectores(self):
        # Create a new window
        segment_window = tkinter.Toplevel()
        segment_window.title("Sectores")

        # maxSegments=4

        texto = tkinter.Label(segment_window, text="Indica el incio y fin de las curvas en orden")
        texto.pack(fill='x', expand=1, pady=20)
        pic = tkinter.Canvas(segment_window, width=self.stream.width, height=self.stream.height)
        pic.pack()
        self.botonAceptar = tkinter.Button(segment_window, text="Aceptar", width=25, command=lambda: aceptar())
        self.botonAceptar.pack(side=tkinter.RIGHT, expand=True)
        self.botonCancelar = tkinter.Button(segment_window, text="Cancelar", width=25, command=lambda: cancelar())
        self.botonCancelar.pack(side=tkinter.RIGHT, expand=True)

        def aceptar():
            if len(self.sectores) < 2:
                alert_window = tkinter.Toplevel()
                alert_window.title("Sectores")
                text = tkinter.Label(alert_window, text=f"Se necesita definir mínimo dos sectores")
                text.pack(fill='x', expand=1, pady=20, padx=20)
            else:
                segment_window.destroy()

        def cancelar():
            self.sectores = None
            segment_window.destroy()

        resul, frame = self.get_frame()
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        if resul:
            imag = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(frame))
            pic.create_image(0, 0, image=imag, anchor=tkinter.NW)

        self.dibujando = False
        self.sectores = []

        def clickado(event):
            self.dibujando = True
            self.sectores.append([0, 0, 0, 0])
            size = len(self.sectores)
            self.sectores[size - 1][0] = event.x
            self.sectores[size - 1][1] = event.y

        def desclickado(event):
            if self.dibujando:
                self.dibujando = False
                size = len(self.sectores)
                self.sectores[size - 1][2] = event.x
                self.sectores[size - 1][3] = event.y
                cv2.line(frame, (self.sectores[size - 1][0], self.sectores[size - 1][1]),
                         (self.sectores[size - 1][2], self.sectores[size - 1][3]), (0, 0, 255), 2)
                self.imag = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(frame))
                pic.create_image(0, 0, image=self.imag, anchor=tkinter.NW)
                print(self.sectores)

        def movimiento(event):
            if self.dibujando == True:
                size = len(self.sectores)
                img = frame.copy()
                p2 = (event.x, event.y)
                cv2.line(img, (self.sectores[size - 1][0], self.sectores[size - 1][1]), p2, (0, 0, 255), 2)
                self.imag = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(img))
                pic.create_image(0, 0, image=self.imag, anchor=tkinter.NW)

        def cerar():
            # si no se han seleccionado mínimo 2 los sectores no se guardan
            if self.sectores is not None:
                if len(self.sectores) < 2:
                    self.sectores = None
                    segment_window.destroy()

                else:
                    segment_window.destroy()

        pic.bind("<Button-1>", clickado)
        pic.bind("<ButtonRelease-1>", desclickado)
        pic.bind("<Motion>", movimiento)
        segment_window.bind("<Destroy>", lambda e: cerar())
        segment_window.mainloop()


    def get_frame(self):
        if self.vc.isOpened():
            resul, frame = self.vc.read()
            if resul:
                # Return a boolean success flag and the current frame converted to BGR
                return (resul, frame)
            else:
                return (resul, None)
        else:
            return (None, None)

    def iniciarCarrera(self):
        self.stream.iniciarCarrera()

    def pararCarrera(self):
        self.stream.pararCarrera()

    def showVideo(self):
        interfaz = threading.Thread(target=self.show)
        interfaz.start()
        procesamiento = threading.Thread(target=self.proc)
        procesamiento.start()

    def show(self):

        self.mutex.acquire()
        try:
            procesado = self.procesado  # Get a local copy
            self.procesado = None
        finally:
            self.mutex.release()

        if procesado is not None:
            self.capture = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(procesado))
            self.video.create_image(0, 0, image=self.capture, anchor=tkinter.NW)

        self.window.after(1, self.show)

    def proc(self):
        while True:
            # resul, frame = self.vc.read()
            resul, frame = self.get_frame()
            if resul:
                if (self.stream.startTracker):
                    resul_proc, data = self.stream.get_tracked_frame(frame)
                    self.saveData(data)
                    f = self.processInfo(resul_proc, frame)
                    self.salidaVideo.write(cv2.cvtColor(f, cv2.COLOR_RGB2BGR))
                else:
                    f=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            self.mutex.acquire()
            try:
                self.procesado = f

            finally:
                self.mutex.release()

            if not self.interfaz_running:
                break

    def saveData(self, data):
        if data[0] is not None:
            self.DataListDerrape.append(data[0])
        self.DataConjuntoDatos.append(data[1])


    def processInfo(self, info, frame):
        # guardar los datos y crear las imagenes
        posCoche = info[0]
        posCulo = info[1]
        trayectoria = info[2]
        ultimaTrayectoria = info[3]
        derrapes = info[4]
        vuelta = info[5]
        self.vueltas = vuelta
        sector = info[6]
        velocidad = info[7]
        tiempoUltimo = info[8]
        tiempoMejor = info[9]
        countFrames = info[10]
        bboxDelante = info[11]
        bboxDetras = info[12]
        posCuloTryect = info[13]
        # derrapando = info[14]
        # cruzada = info[15]

        if bboxDelante is not None:
            x, y, z, t = [int(i) for i in bboxDelante]
            cv2.rectangle(frame, (x, y), (x + z, y + t), (0, 255, 255), 2)

        if bboxDetras is not None:
            x, y, z, t = [int(i) for i in bboxDetras]
            cv2.rectangle(frame, (x, y), (x + z, y + t), (0, 255, 0), 2)

        if posCoche is not None:
            cv2.circle(frame, (int(posCoche[0]), int(posCoche[1])), radius=2, color=(0, 0, 255), thickness=-1)

        if self.mostrarDerrapes and posCulo is not None and posCuloTryect is not None:  # si esta activada la opcion de mostrarlos
            if info[14]:
                cv2.line(frame, (int(posCulo[0]), int(posCulo[1])), (int(posCuloTryect[0]), int(posCuloTryect[1])),
                         (255, 255, 255), 2)
            else:
                cv2.line(frame, (int(posCulo[0]), int(posCulo[1])), (int(posCuloTryect[0]), int(posCuloTryect[1])),
                         (255, 255, 255), 1)

        if self.dobleTrayectoria:
            for p in ultimaTrayectoria:
                t = (int(p[0]), int(p[1]))
                cv2.circle(frame, t, radius=1, color=(255, 150, 0), thickness=-1)

        for p in trayectoria:
            t = (int(p[0]), int(p[1]))
            cv2.circle(frame, t, radius=2, color=(0, 0, 255), thickness=-1)

        if self.meta is not None:
            cv2.line(frame, (self.meta[0], self.meta[1]), (self.meta[2], self.meta[3]), (0, 0, 255), 2)

        # para saber el numero de filas (es decir el numero de sectores) se dividen el num total de elementos entre el num de columnas (4)
        sect = np.array(self.sectores)
        numSectores = int(sect.size / 4)
        if self.sectores is not None:
            for i in range(0, numSectores):
                cv2.line(frame, (sect[i, 0], sect[i, 1]), (sect[i, 2], sect[i, 3]),(255, 255, 0), 2)

        # muestra los derrapes
        if self.mostrarDerrapes:
            if derrapes is not None and derrapes != []:
                for i in range(0, len(derrapes)):
                    cv2.circle(frame, (derrapes[i][0], derrapes[i][1]), radius=2, color=(255, 255, 255),
                               thickness=-1)
                    cv2.circle(frame, (derrapes[i][2], derrapes[i][3]), radius=2, color=(120, 255, 255),
                               thickness=-1)

        fuente = cv2.FONT_HERSHEY_SIMPLEX
        tamaño = 0.7
        color = (255, 0, 0)  # Blue color in BGR format
        grosor = 2
        posicion = (10, 30)
        if info[15] is not None:
            # Draw the text on the frame
            cv2.putText(frame, f"Vueltas: {vuelta}", posicion, fuente, tamaño, color, grosor)

        posicion = (10, 60)
        cv2.putText(frame, f"Sector: {sector + 1}", posicion, fuente, tamaño, color, grosor)
        posicion = (200, 30)
        cv2.putText(frame, f"Frame: {countFrames}", posicion, fuente, tamaño, (0, 75, 0), grosor)

        posicion = (200, 60)
        cv2.putText(frame, f"PWM: {velocidad}", posicion, fuente, tamaño, (0, 75, 0), grosor)

        if tiempoUltimo is not None:
            cv2.rectangle(frame, (380, 10), (640, 60), (255, 255, 255), -1)
            fuente = cv2.FONT_HERSHEY_SIMPLEX
            tamaño = 0.6
            color = (50, 20, 100)  # Blue color in BGR format
            grosor = 2
            posicion = (400, 30)
            cv2.putText(frame, f"Ultima vuelta: {tiempoUltimo:.3f} s", posicion, fuente, tamaño, color, grosor)

            posicion = (400, 50)
            cv2.putText(frame, f"Mejor Vuelta: {tiempoMejor:.3f} s", posicion, fuente, tamaño, color, grosor)

        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    def saveValues(self):

        if self.generarDatos:

            self.stream.algoritmo.saveData(self.vueltas)
            with open("derrapes.csv", "w", newline="") as archivoCSV:
                fichero = csv.DictWriter(archivoCSV, fieldnames=["frame", "derrape"])
                fichero.writeheader()
                for fila in self.DataConjuntoDatos:
                    fichero.writerow({"frame": fila[0], "derrape": fila[1]})

            with open("datos.csv", "w", newline="") as archivoCSV:
                fichero = csv.DictWriter(archivoCSV,
                                         fieldnames=["Frame", "PWM", "Meta", "Sector", "Tiempo", "Dif tiempo",
                                                     "Pos front X", "Pos front Y",
                                                     "Dist puntos", "Derrapo", "Dist derrape", "Pos back X",
                                                     "Pos back Y", ])
                fichero.writeheader()
                count = 0
                for fila in self.DataConjuntoDatos:
                    count += 1

                    if fila[6] is None:
                        px = None
                        py = None
                    else:
                        px = fila[6][0]
                        py = fila[6][1]

                    if fila[10] is None:
                        pxBack = None
                        pyBack = None
                    else:
                        pxBack = fila[10][0]
                        pyBack = fila[10][1]

                    fichero.writerow(
                        {"Frame": fila[0], "PWM": fila[1], "Meta": fila[2], "Sector": fila[3], "Tiempo": fila[4],
                         "Dif tiempo": fila[5], "Pos front X": px, "Pos front Y": py, "Dist puntos": fila[7],
                         "Derrapo": fila[8], "Dist derrape": fila[9], "Pos back X": pxBack, "Pos back Y": pyBack})


class Capturador:
    def __init__(self, width, hight):
        self.algoritmo = AlgotirmoVelocidad()
        # Se crea el VideoCaptureObject
        self.initial_box = None
        self.actual_box = None
        self.lastTwo = []
        self.tracker = None  # indica si se inició el tracker

        # Se obtienen las dimensiones del video
        self.width = width
        self.height = hight
        self.selectedColor = None  # Color seleccionado almacenado en el modelo de color HSV
        self.backColor = None
        self.contornoEtiq = None
        self.contornoEtiqDetras = None
        self.trayectoria = []
        self.ultimaTrayectoria = []
        self.reiniciarTracker = False  # indica si hay que volver a reiniciar el tracker por que aun no se encontró
        self.countFrames = 0  # mecanismo de control
        self.started = False  # indica si se ha empezado ya a andar
        self.meta = None  # [initx, inity, endx, endy] -> coordenadas del punto de inicio y fin de meta
        self.ladoMeta = None  # variable para saber de que leado de la meta empieza el coche
        self.cruzada = None  # Indica si la meta ya fue cruzada
        self.sectores = None
        self.ladoSector = [None, None, None, None]
        self.trackLost = False  # Indica si se perdió el tracker, para que cuando se restablezca se actualice el sector
        self.startRace = False
        self.tiempoVuelta = [None, None]  # se almacena el tiempo de inico y fin para calcular el tiempo de vuelta
        self.ultimoTiempo = None  # tiempo de la ultima vuelta dada
        self.mejorTiempo = None  # tiempo de la mejor vuelta
        self.tiempoSectores = []
        self.tsect = 0  # va almacenando el tiempo mientras el sector no se cruza para determinar el tiempo antes de cuzarlo
        self.startTracker = False

        self.startDetctionDerape = False  # indica si se comienza con la detedcción de derrape
        self.derrapando = False  # indica si se está en medio de un derrape
        self.ultimoDerrape = [0, 0, 0, 0]  # indica la posición de inicio y fin del ultimo derrape detectado
        self.derrapes = None

        self.distanciaCulo = []
        self.listDerrape = None

        # almacenan el tiempo y posicion anterior para poder calcular la diferencia con el actual
        self.listaTiempo = []
        self.listaPosiciones = []

        self.valorPWM = None
        self.valorTiempo = None
        self.valorDifTiempos = None
        self.valorPosicion = None
        self.valorDistancia = None
        self.valorMetaCruzada = None
        self.valorSectorCruzado = None
        self.valorPosicionCulo = None
        self.valorDerrapo = None
        self.valorDistanciaDerrape = None

        self.conjuntoDatos = []

        # obtiene el tiempo consumido por el algoritmo
        self.tiempoAlgDerrape = []
        self.tiempoAlgCalculoDistancia = []
        self.trayectoriaAlgoritmo = None

        self.frame = None
        self.bboxdelante = None
        self.bboxdetras = None
        self.closest_point = (0,0)


    def ini_tracker(self, meta, sectores, color, colorDetras, frame):
        self.meta = meta
        self.ladoMeta = None
        self.sectores = np.array(sectores)
        self.ladoSector = [None, None, None, None]
        self.tiempoSectores = [0, 0, 0, 0]
        self.selectedColor = color
        self.backColor = colorDetras
        print(f"Array numpy: {np.array(sectores)}")
        self.cruzada = None
        self.ladoMeta = None
        self.tracker = True
        arduino.write(('v' + str(0) + '\n').encode())
        self.initial_box = cv2.selectROI("Seleccion coche", frame, False)
        self.actual_box = self.initial_box
        # self.tracker.init(frame, self.initial_box)
        cv2.destroyWindow("Seleccion coche")
        self.vueltas = 0
        self.sector = 0
        self.velocidades = [70, 60, 70, 60]
        self.velocidad = None
        self.startTracker = True

    def end_tracker(self):
        self.tracker = None
        self.startTracker = False
        self.started = False
        self.cruzada = None
        self.startDetctionDerape = False
        self.derrapando = False  # indica si se está en medio de un derrape
        self.ultimoDerrape = [0, 0, 0, 0]  # indica la posición de inicio y fin del ultimo derrape detectado
        self.derrapes = None
        self.trayectoria = []
        self.ultimaTrayectoria = []
        self.pararCarrera()
        self.countFrames = 0

    def iniciarCarrera(self):
        if self.tracker is not None:
            self.startRace = True
            vaciar_buffer()
            # se inicia segun el sector en el que se encuentre
            arduino.write(('v' + str(self.algoritmo.velocidad[0]) + '\n').encode())
            self.velocidad = self.algoritmo.velocidad[0]

    def pararCarrera(self):
        self.startRace = False
        self.tiempoVuelta = [None, None]
        self.ultimoTiempo = None
        self.mejorTiempo = None
        self.cruzada = None
        self.vueltas = 0
        vaciar_buffer()
        arduino.write(('v' + str(0) + '\n').encode())
        vaciar_buffer()

    def get_tracked_frame(self, frame):
        self.frame = frame

        self.countFrames += 1

        if not self.reiniciarTracker and self.startTracker:

            # se busca la nueva etiqueta usando de referencia el Bbox del anterior frame
            contornos = self.getBboxByColorInsideTracker(frame, self.actual_box)

            if contornos is not None:
                contornoPorColor, contornoDetras = contornos
                # valore del nuevo Bbox
                x, y, z, t = [int(i) for i in self.actual_box]

                if self.contornoEtiq is None:
                    # Se almacena el tamaño del contorno inicial
                    self.contornoEtiq = cv2.contourArea(contornoPorColor)

                if self.contornoEtiqDetras is None and contornoDetras is not None:
                    self.contornoEtiqDetras = cv2.contourArea(contornoDetras)
            else:
                print("No se encuentra etiqueta")
                Bbox = self.getTrackerLostBbox(frame)
                if (Bbox is not None):
                    trackerBbox, etiquetaBbox, etiquetaDetras = Bbox

                    self.setByContornoEtiqueta(frame, etiquetaBbox, etiquetaDetras)

            if contornos is not None:
                contornoPorColor, contornoDetras = contornos
                # Se dibuja el bounding box por el color
                etiquetaBbox = cv2.boundingRect(contornoPorColor)
                if contornoDetras is not None:
                    etiquetaDetras = cv2.boundingRect(contornoDetras)
                else:
                    etiquetaDetras = None
                self.setByContornoEtiqueta(frame, etiquetaBbox, etiquetaDetras)


        else:
            # Se ejecuta cuando la readquisición anterior no tuvo éxito
            print(f"Reinicio fallido - frame: {self.countFrames} ")
            Bbox = self.getTrackerLostBbox(frame)
            if (Bbox is not None):
                trackerBbox, etiquetaBbox, etiquetaDetras = Bbox

                self.setByContornoEtiqueta(frame, etiquetaBbox, etiquetaDetras)




        self.conjuntoDatos = (self.countFrames, self.velocidad, self.valorMetaCruzada,
                                   self.valorSectorCruzado, self.valorTiempo, self.valorDifTiempos,
                                   self.valorPosicion, self.valorDistancia, self.valorDerrapo,
                                   self.valorDistanciaDerrape, self.valorPosicionCulo)


        # posDelante, PosDetras, trayect, UltimaTrayect, zonaDerrape, vueltas, sector, pwm, tiempoUltimo, tiempoMejor, countFraes, bboxdelante, bboxdetras, posculotray, derrapando, cruzada
        infoForFrame = [self.valorPosicion, self.valorPosicionCulo, self.trayectoria, self.ultimaTrayectoria, self.derrapes, self.vueltas, self.sector, self.velocidad, self.ultimoTiempo, self.mejorTiempo, self.countFrames, self.bboxdelante, self.bboxdetras, self.closest_point, self.derrapando, self.cruzada]

        dataToStore = [self.listDerrape, self.conjuntoDatos]
        self.listDerrape = None

        self.valorTiempo = None
        self.valorDifTiempos = None
        self.valorPosicion = None
        self.valorDistancia = None
        self.valorMetaCruzada = None
        self.valorSectorCruzado = None
        self.valorDerrapo = None
        self.valorDistanciaDerrape = None
        self.valorPosicionCulo = None

        return infoForFrame, dataToStore



    def setByContornoEtiqueta(self, frame, etiquetaBbox, etiquetaDetras):
        x, y, z, t = [int(i) for i in etiquetaBbox]
        self.bboxdelante=etiquetaBbox
        self.bboxdetras=etiquetaDetras
        px = x + z / 2
        py = y + t / 2

        if self.listaPosiciones == []:
            self.valorDistancia = None
        else:
            ultimaPosicion = self.listaPosiciones[-1]
            distance = round(math.sqrt(abs(ultimaPosicion[0] - px) ** 2 + abs(ultimaPosicion[1] - py) ** 2), 3)
            self.valorDistancia = distance

        self.listaPosiciones.append((px, py))
        self.valorPosicion = (px, py)

        if etiquetaDetras is not None:
            x, y, z, t = [int(i) for i in etiquetaDetras]
            # posición de la etiqiueta trasera
            pxCulo = x + z / 2
            pyCulo = y + t / 2
            self.valorPosicionCulo = (pxCulo, pyCulo)
        else:
            self.valorPosicionCulo = None

        t = round(time.time() * 1000, 3)

        if self.listaTiempo == []:
            self.valorDifTiempos = None
        else:
            self.valorDifTiempos = t - self.listaTiempo[-1]

        self.listaTiempo.append(t)
        self.valorTiempo = t

        pointX = int(px)
        pointY = int(py)
        if self.trackLost:
            # Si el tracker se perdio se debe de recalcular el sector en el que se encuentra
            self.reloadSector((pointX, pointY))
            self.trackLost = False

        if self.ladoMeta == None:
            # En el primer frame se configura de que lado de la meta sale el coche
            self.configureLadoMeta((pointX, pointY))

        if self.check_crossing_finish_line((pointX, pointY)):

            self.vueltas += 1
            self.ultimoTiempo = (self.tiempoVuelta[1] - self.tiempoVuelta[0]) / 1000
            if (self.mejorTiempo is None or self.ultimoTiempo < self.mejorTiempo):
                self.mejorTiempo = self.ultimoTiempo

            self.tiempoVuelta[0] = self.tiempoVuelta[1]

            self.ultimaTrayectoria = self.trayectoria
            self.trayectoria = []

            self.algoritmo.setTrayectoria(self.trayectoriaAlgoritmo)

        t = round(time.time() * 1000, 3)

        umbral, velocidad = self.algoritmo.setVelocidad((pointX, pointY), self.countFrames)

        u = round(time.time() * 1000, 3) - t
        self.tiempoAlgCalculoDistancia.append(u)
        if velocidad is not None:
            self.velocidad = velocidad

        self.detectarDerrape(etiquetaDetras, frame)
        self.getSector((pointX, pointY))
        self.trayectoria.append((px, py))
        if self.trayectoriaAlgoritmo is not None and self.vueltas == 0:
            # se obtine los puntos de la primera vuelta
            # Se empiezan a almacenar cuando cruza la meta al salir
            self.trayectoriaAlgoritmo.append((px, py))

        # actualizar los ultimos dos puntos
        if len(self.lastTwo) < 2:
            self.lastTwo.append((pointX, pointY))
        else:
            self.lastTwo[0] = self.lastTwo[1]
            self.lastTwo[1] = (pointX, pointY)

    def detectarDerrape(self, etiquetaDetras, frame):
        # solo si se ha detectado la etiqueta de atrás
        if etiquetaDetras is not None:
            x, y, z, t = [int(i) for i in etiquetaDetras]
            px = x + z / 2
            py = y + t / 2

            # si ya se cruzó la meta al comenzar la carrera
            if self.cruzada is not None:

                min_distance = 100
                self.closest_point = (0, 0)

                trayectoria = self.ultimaTrayectoria + self.trayectoria
                lon = len(trayectoria)
                if lon > 1:

                    for i in range(lon - 1, 0, -1):
                        start = trayectoria[i]
                        end = trayectoria[i - 1]
                        d = self.distance_to_line_segment((px, py), start, end)
                        distance, point = d

                        if distance <= min_distance:
                            min_distance = distance
                            self.closest_point = point

                        else:
                            if distance - min_distance > 3:
                                break

                    if not self.startDetctionDerape:
                        # detecta la primera vez que el culo tiene diatncia 0 a la trayectoria
                        # Es decir el culo alcanzó el inicio de l atrayectoria y por lo tanto ya se empieza con la detección del derrape
                        if min_distance <= 1:
                            self.startDetctionDerape = True
                    else:

                        if min_distance > 8:
                            self.listDerrape = (self.countFrames, min_distance)
                            self.valorDerrapo = 1
                            if not self.derrapando:
                                self.derrapando = True
                                self.ultimoDerrape[0] = int(px)
                                self.ultimoDerrape[1] = int(py)
                        else:
                            if self.derrapando:
                                self.ultimoDerrape[2] = int(px)
                                self.ultimoDerrape[3] = int(py)
                                t = round(time.time() * 1000, 3)
                                self.derrapes = self.algoritmo.derrapeDetected(self.ultimoDerrape, self.vueltas,
                                                                               self.countFrames)
                                u = round(time.time() * 1000, 3) - t
                                self.tiempoAlgDerrape.append(u)
                                print(f"Derrape en frame: {u} Tiempo total de procesado: {self.countFrames}")

                                self.ultimoDerrape = [0, 0, 0, 0]
                                self.derrapando = False
                            self.valorDerrapo = 0

                        self.valorDistanciaDerrape = min_distance
                        self.distanciaCulo.append((self.countFrames, min_distance))

    def distance_to_line_segment(self, point, inicio, fin):
        # Vector del segmento, desde el punto de inicio al de fin
        vectorSegmento = (fin[0] - inicio[0], fin[1] - inicio[1])

        # Vector desde el punto de inicio del segmento al culo del coche
        vetorCuloCoche = (point[0] - inicio[0], point[1] - inicio[1])

        # Distancia desde el punto de inicio al de fin
        tamañoSemento = math.sqrt(vectorSegmento[0] ** 2 + vectorSegmento[1] ** 2)

        # Si tiene tamaño 0, la distancia es la distancia a la trayectoria es la distancia al punto de inicio (o de fin)
        if tamañoSemento == 0:
            return math.sqrt(vetorCuloCoche[0] ** 2 + vetorCuloCoche[1] ** 2), inicio

        # producto escalar para obtener t que indica de forma perpendicular al segmento cuan cerca (entre 0 y 1) se encuentra del punto de inicio
        productoEscalar = (vetorCuloCoche[0] * vectorSegmento[0] + vetorCuloCoche[1] * vectorSegmento[1])
        t = productoEscalar / (
                    tamañoSemento ** 2)  # normalización de los valores entre 0 y el tamaño del segmento a entre 0 y 1

        # si es menor a 0 la perpendicular cuadra antes del punto de inicio, por loq ue devuelve la distancia al inicio
        if t < 0:
            return math.sqrt(vetorCuloCoche[0] ** 2 + vetorCuloCoche[1] ** 2), inicio

        # si es mayot a 1 la perpendicular cuadra despues del punto de fin, por loq ue devuelve la distancia al fin
        if t > 1:
            return math.sqrt((point[0] - fin[0]) ** 2 + (point[1] - fin[1]) ** 2), fin

        # con t se calcula el punto en el sengmento mas proximo al culo del coche (por donde pasa la perpendicular a la trayectoria)
        puntoProximo = (inicio[0] + t * vectorSegmento[0], inicio[1] + t * vectorSegmento[1])

        # Se calcula la distancia del cuclo del coche al punto mas proximo de la trayectoria
        distance = math.sqrt((point[0] - puntoProximo[0]) ** 2 + (point[1] - puntoProximo[1]) ** 2)
        return distance, puntoProximo


    def getTrackerLostBbox(self, frame):
        #Readquisicion del seguimeinto

        contour = self.getBboxByColor(frame)
        if contour is not None:
            contornoPorColor, contornoDetras = contour
            x, y, w, h = cv2.boundingRect(contornoPorColor)  # calculated Bbox of the color tag
            if contornoDetras is not None:
                etiquetaDetras = cv2.boundingRect(contornoDetras)
            else:
                etiquetaDetras = None

            self.lastTwo = []
            self.lastTwo.append((int(x + w / 2), int(y + h / 2)))

            # get inital Bbox to create one with the same dimensions
            xinit, yinit, winit, hinit = self.initial_box

            # conociendo el Bbox de la etiqueta se calcula el centro de la etiqueta y con esto el centro del Bbox del coche
            pointX = int(x + w / 2) - winit / 3
            pointY = int(y + h / 2)

            Bbox = int(pointX) - int(winit / 2), int(pointY - hinit / 2), winit, hinit
            self.trackLost = True
            self.reiniciarTracker = False

            etiquetaBbox = x, y, w, h
            return (Bbox, etiquetaBbox, etiquetaDetras)
        else:
            self.bboxdelante = None
            self.bboxdetras = None
            self.reiniciarTracker = True
            return None

    # get the Bbox based on the color analzing all the frame
    def getBboxByColor(self, frame):
        if self.selectedColor is not None:
            f = frame.copy()
            if self.reiniciarTracker == True:  # se filtra por el Bbox del ROI
                mask = np.zeros(frame.shape[:2], dtype=np.uint8)
                filtered = cv2.bitwise_and(frame, frame, mask=mask)


            if self.ultimaTrayectoria != []:  # si existe trayectoria
                img = self.getFrameTrayectoria(frame)  # se obtiene el frame filtrado por la trayectoria
                f = self.getFrameTrayectoria(frame)

                frameHSV = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

            else:  # si no existe trayectoria no se puede filtrar por esta

                frameHSV = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

            # DETECCIÓN ETIQUETA DELANTERA
            # con la imagen filtrada se busca por color obteniendo los contornos
            minS = (self.selectedColor[1] - 60)
            if minS < 1: minS = 1
            # Se establecen los rangos de color a trackear
            minColor = np.array([(self.selectedColor[0] - 15) % 255, minS, 100])
            maxColor = np.array([(self.selectedColor[0] + 15) % 255, 255, 255])

            # Se crea una mascara con los pixeles que estan en el rango
            mask = cv2.inRange(frameHSV, minColor, maxColor)
            intersec = cv2.bitwise_and(frame, frame, mask=mask)

            # se obtienen los contornos de la mascara
            contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

            # DETECCION ETIQUETA TRASERA
            minS = (self.backColor[1] - 60)
            if minS < 1: minS = 1
            # Se establecen los rangos de color a trackear
            minColor = np.array([(self.backColor[0] - 15) % 255, minS, 100])
            maxColor = np.array([(self.backColor[0] + 15) % 255, 255, 255])

            # Se crea una mascara con los pixeles que estan en el rango
            mask = cv2.inRange(frameHSV, minColor, maxColor)
            intersec = cv2.bitwise_and(frame, frame, mask=mask)

            # se obtienen los contornos de la mascara
            backContours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

            if len(contours) > 0:

                if len(backContours) > 0:
                    cortornoDetras = max(backContours, key=cv2.contourArea)
                    if self.contornoEtiqDetras is not None:
                        if cv2.contourArea(cortornoDetras) < self.contornoEtiqDetras * 0.25:
                            # se declara como no encontrado
                            cortornoDetras = None
                else:
                    cortornoDetras = None

                contorno = max(contours, key=cv2.contourArea)
                if cv2.contourArea(contorno) < self.contornoEtiq * 0.7:
                    # Si el contorno es tres veces mas pequeño se considera Nulo
                    return None
                else:
                    return (contorno, cortornoDetras)
            else:
                return None
        else:
            return None

    def getFrameTrayectoria(self, frame):
        t = round(time.time() * 1000, 3)
        # mascara negra de las dimensiones del fotograma
        mask = np.zeros_like(frame)

        tracye = [tuple(map(int, tpl)) for tpl in self.ultimaTrayectoria]
        # Dibuja la trayectoria en la mascara
        cv2.polylines(mask, [np.array(tracye, dtype=np.int32)], isClosed=False, color=(255, 255, 255), thickness=35)

        # Se aplica la máscara al fotograma
        result = cv2.bitwise_and(frame, mask)
        t = round(time.time() * 1000, 3) - t
        return result

    def getAreaToSearch(self):
        long = len(self.lastTwo)
        # si es primera ej coger el bbox
        if long == 0:
            return self.initial_box, None, None
        else:
            x, y, w, h = [int(i) for i in self.initial_box]

            # obtenemos el valor mas largo que indicara el largo del coche
            if w > h:
                l = w
            else:
                l = h

            if long == 1:
                # si es la segunda obtener el bbox desde el otro punto
                centro = self.lastTwo[0]
                p3 = centro

            else:
                p1, p2 = self.lastTwo
                p1 = np.array(self.lastTwo[0])
                p2 = np.array(self.lastTwo[1])

                #p3 -> punto extrapolado
                p3 = p2 + (p2 - p1)

                # vector que define la trayectoria
                v = p1 - p2

                mod = np.linalg.norm(v)

                # Factor de escala del coche para que el vector tenga de modulo la distancia del punto de la etiqueta
                # al centro del coche (largo del coche / 2)
                if mod != 0:

                    factor_escala = (l / 3) / mod

                    # Se rescala el vector para que tenga de modulo dicha distancia
                    v = v * factor_escala  # vector q dado el centro de la etiqueta devuelve el centro del coche
                    centro = p3 + v
                else:
                    centro = p3

            # Bbox de búsqueda
            Bbox = [centro[0] - l / 2 - 10, centro[1] - l / 2 - 10, l + 20, l + 20]

            x, y, w, h = [int(i) for i in Bbox]

            if x < 0:
                x = 1
            if y < 0:
                y = 1
            if x + w > self.width:
                w = self.width - x - 1
            if y + h > self.height:
                h = self.height - y - 1

            return (x, y, w, h), (int(centro[0]), int(centro[1])), (int(p3[0]), int(p3[1]))

    # devuelve el contorno en funcion a un color analizando solo la parte de dentro del Bbox
    def getBboxByColorInsideTracker(self, frame, Bbox):
        img = frame
        roi, centro, p3 = self.getAreaToSearch()
        x, y, w, h = [int(i) for i in roi]

        # se aplica el filtro de trayectoria
        if self.ultimaTrayectoria != []:
            frame = self.getFrameTrayectoria(frame)

        # Se crea la máscara con las dimensiones del frame
        mask = np.zeros(frame.shape[:2], dtype=np.uint8)

        # Se dibuja un rectángulo en la máscara correspondiente al área donde se va a buscar
        cv2.rectangle(mask, (x, y), (x + w, y + h), 255, -1)

        # se crea la imagen filtrada por la máscara fusionando la máscara y el frame
        filtered_frame = cv2.bitwise_and(frame, frame, mask=mask)


        if self.selectedColor is not None and self.backColor is not None:
            # Buscaremos en la imagen filtrada para que solo busque dentro del Bbox
            frameHSV = cv2.cvtColor(filtered_frame, cv2.COLOR_BGR2HSV)

            minS = (self.selectedColor[1] - 60)
            if minS < 1: minS = 1
            # Se establecen los rangos de color a trackear
            minColor = np.array([(self.selectedColor[0] - 15) % 255, minS, 100])
            maxColor = np.array([(self.selectedColor[0] + 15) % 255, 255, 255])

            # Se crea una mascara con los pixeles que estan en el rango
            mask = cv2.inRange(frameHSV, minColor, maxColor)

            # se obtienen los contornos de la mascara
            contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

            minS = (self.backColor[1] - 60)
            if minS < 1: minS = 1
            # Se establecen los rangos de color a trackear
            minColor = np.array([(self.backColor[0] - 15) % 255, minS, 100])
            maxColor = np.array([(self.backColor[0] + 15) % 255, 255, 255])

            # Se crea una mascara con los pixeles que estan en el rango
            mask = cv2.inRange(frameHSV, minColor, maxColor)

            # se obtienen los contornos de la mascara
            backContours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

            if len(contours) > 0:

                if len(backContours) > 0:
                    cortornoDetras = max(backContours, key=cv2.contourArea)
                    if self.contornoEtiqDetras is not None:
                        if cv2.contourArea(cortornoDetras) < self.contornoEtiqDetras * 0.25:
                            # se declara como no encontrado
                            cortornoDetras = None

                else:
                    cortornoDetras = None

                contorno = max(contours, key=cv2.contourArea)
                if self.contornoEtiq is None:
                    return (contorno, cortornoDetras)
                else:
                    if cv2.contourArea(contorno) < self.contornoEtiq * 0.3:
                        # Si el contorno es tres veces mas pequeño se considera Nulo
                        return None
                    else:
                        return (contorno, cortornoDetras)



            else:
                return None
        else:
            return None

    # Según la posición inical configura el lado de la meta por el que se entra
    def configureLadoMeta(self, car_position):
        # Se mira en que lado de la linea empieza el coche
        AB = np.array((self.meta[2], self.meta[3])) - np.array((self.meta[0], self.meta[1]))
        AP = np.array(car_position) - np.array((self.meta[2], self.meta[3]))
        cross_product = np.cross(AB, AP)
        if cross_product >= 0:
            # Lado positivo entonces True
            self.ladoMeta = True
            print("configurado lado positivo")
        elif cross_product < 0:
            # Lado negativo entonces False
            self.ladoMeta = False
            print("configurado lado negativo")

    def check_crossing_finish_line(self, car_position):
        pointVector = np.array(car_position) - np.array((self.meta[2], self.meta[3]))
        dist = math.sqrt(pointVector[0] ** 2 + pointVector[1] ** 2)
        if int(dist) < (self.initial_box[2] * 1.5) or int(dist) < (self.initial_box[3] * 1.5):
            metaVector = np.array((self.meta[2], self.meta[3])) - np.array((self.meta[0], self.meta[1]))
            productoVectorial = np.cross(metaVector, pointVector)
            if self.ladoMeta == True:
                if self.cruzada == None:  # si aun no se ha cruzado la meta
                    self.tiempoVuelta[1] = round(time.time() * 1000, 3)
                    if productoVectorial < 0:
                        self.cruzada = True
                        self.getTiempoVuelta(car_position)
                        print("SALIDA")
                        self.trayectoriaAlgoritmo = []
                        self.valorMetaCruzada = 1
                    else:
                        self.valorMetaCruzada = 0

                    return False

                else:
                    if self.cruzada == True:
                        self.tiempoVuelta[1] = round(time.time() * 1000, 3)
                        if productoVectorial > 0:
                            self.cruzada = False
                        self.valorMetaCruzada = 0
                        return False
                    else:
                        if productoVectorial < 0:
                            # Acaba de cruzar la meta
                            self.cruzada = True
                            self.getTiempoVuelta(car_position)
                            self.valorMetaCruzada = 1
                            return True
                        else:
                            self.valorMetaCruzada = 0
                            self.tiempoVuelta[1] = round(time.time() * 1000, 3)
                            return False


            elif self.ladoMeta == False:
                if self.cruzada == None:
                    if productoVectorial > 0:
                        self.cruzada = True
                        self.getTiempoVuelta(car_position)
                        print("SALIDA")
                        self.valorMetaCruzada = 1
                    else:
                        self.valorMetaCruzada = 0
                    self.tiempoVuelta[1] = round(time.time() * 1000, 3)
                    return False

                else:
                    if self.cruzada == True:
                        self.tiempoVuelta[1] = round(time.time() * 1000, 3)
                        if productoVectorial < 0:
                            self.cruzada = False
                        self.valorMetaCruzada = 0
                        return False
                    else:
                        if productoVectorial > 0:
                            # Acaba de cruzar la meta
                            self.cruzada = True
                            self.getTiempoVuelta(car_position)
                            print("Cruzó la meta")
                            self.valorMetaCruzada = 1
                            return True
                        else:
                            self.valorMetaCruzada = 0
                            self.tiempoVuelta[1] = round(time.time() * 1000, 3)
                            return False


        else:
            self.valorMetaCruzada = 0
            return False

    def getTiempoVuelta(self, car_position):

        if self.tiempoVuelta[0] is None:
            if self.tiempoVuelta[1] is not None:
                if self.trayectoria == None or len(self.trayectoria) == 0:
                    preMeta = (int(self.ultimaTrayectoria[-1][0]), int(self.ultimaTrayectoria[-1][1]))
                else:
                    preMeta = (int(self.trayectoria[-1][0]), int(self.trayectoria[-1][1]))
                postMeta = car_position

                tiempoPost = round(time.time() * 1000, 3)
                tiempoPre = self.tiempoVuelta[1]

                distPre = abs(self.meta[0] - preMeta[0])
                distPost = abs(self.meta[0] - postMeta[0])

                tiempoMeta = (distPre * (tiempoPost - tiempoPre)) / (
                            distPre + distPost)  # tiempo desde el punto pre-meta a meta
                tiempoMeta = tiempoPre + tiempoMeta  # tiempo por al que pasa por la meta

                self.tiempoVuelta[0] = tiempoMeta

        else:
            if self.trayectoria == None or len(self.trayectoria) == 0:
                preMeta = (int(self.ultimaTrayectoria[-1][0]), int(self.ultimaTrayectoria[-1][1]))
            else:
                preMeta = (int(self.trayectoria[-1][0]), int(self.trayectoria[-1][1]))
            postMeta = car_position

            tiempoPost = round(time.time() * 1000, 3)
            tiempoPre = self.tiempoVuelta[1]

            if (abs(self.meta[0] - self.meta[2]) < abs(self.meta[1] - self.meta[3])):
                # meta en sentido vertical
                # distancias a meta desde cada punto
                distPre = abs(self.meta[0] - preMeta[0])
                distPost = abs(self.meta[0] - postMeta[0])

            else:
                # meta en sentido horizontal
                # distancias a meta desde cada punto
                distPre = abs(self.meta[1] - preMeta[1])
                distPost = abs(self.meta[1] - postMeta[1])

            # Se interpola el tiempo en la meta conociendo el tiemo en cada punto y la distancia
            tiempoMeta = (distPre * (tiempoPost - tiempoPre)) / (
                        distPre + distPost)  # tiempo desde el punto pre-meta a meta
            tiempoMeta = tiempoPre + tiempoMeta  # tiempo por al que pasa por la meta

            self.tiempoVuelta[1] = tiempoMeta

    def configureLadoSector(self, car_position):
        # Se mira en que lado de la linea empieza el coche
        sectorVector = np.array((self.sectores[self.sector, 2], self.sectores[self.sector, 3])) - np.array(
            (self.sectores[self.sector, 0], self.sectores[self.sector, 1]))
        toCarVector = np.array(car_position) - np.array((self.sectores[self.sector, 2], self.sectores[self.sector, 3]))
        cross_product = np.cross(sectorVector, toCarVector)
        if cross_product >= 0:
            # Lado positivo entonces True
            self.ladoSector[self.sector] = True
        elif cross_product < 0:
            # Lado negativo entonces False
            self.ladoSector[self.sector] = False

    def getSector(self, car_position):

        carVector = np.array(car_position) - np.array((self.sectores[self.sector, 2], self.sectores[self.sector, 3]))
        dist = math.sqrt(carVector[0] ** 2 + carVector[1] ** 2)
        if int(dist) < (self.initial_box[2] * 1.3) or int(dist) < (self.initial_box[3] * 1.3):

            sectorVector = np.array((self.sectores[self.sector, 2], self.sectores[self.sector, 3])) - np.array(
                (self.sectores[self.sector, 0], self.sectores[self.sector, 1]))
            productoVectorial = np.cross(sectorVector, carVector)

            if self.ladoSector[self.sector] == None:
                if productoVectorial >= 0:
                    # Lado positivo entonces True
                    self.ladoSector[self.sector] = True
                elif productoVectorial < 0:
                    # Lado negativo entonces False
                    self.ladoSector[self.sector] = False

            if self.ladoSector[self.sector] == True:

                if productoVectorial < 0:
                    if self.trayectoria == []:
                        preSector = (int(self.ultimaTrayectoria[-1][0]), int(self.ultimaTrayectoria[-1][1]))
                    else:
                        preSector = (int(self.trayectoria[-1][0]), int(self.trayectoria[-1][1]))
                    postSector = car_position

                    tiempoPost = round(time.time() * 1000, 3)
                    tiempoPre = self.tsect

                    distPre = abs(self.meta[0] - preSector[0])
                    distPost = abs(self.meta[0] - postSector[0])

                    tiempoSector = (distPre * (tiempoPost - tiempoPre)) / (
                                distPre + distPost)  # tiempo desde el punto pre-meta a meta
                    tiempoSector = tiempoPre + tiempoSector  # tiempo en el que se cruzo e sector

                    p = self.sector + 1
                    if p == self.sectores.size / 4:
                        p = 0
                    if self.tiempoSectores[self.sector] != 0:
                        self.tiempoSectores[self.sector] = tiempoSector - self.tiempoSectores[self.sector]
                        self.tiempoSectores[p] = tiempoSector
                    else:
                        self.tiempoSectores[p] = tiempoSector

                    self.sector += 1

                    if self.sector >= self.sectores.size / 4:
                        self.sector = 0
                    self.valorSectorCruzado = self.sector + 1
                    if self.startRace:
                        # se cambia la velocidad a la del nuevo sector
                        vaciar_buffer()

                    # self.ladoSector[self.sector]=None
                else:
                    self.tsect = round(time.time() * 1000, 3)
                    self.valorSectorCruzado = 0


            elif self.ladoSector[self.sector] == False:
                if productoVectorial > 0:

                    if self.trayectoria == []:
                        preSector = (int(self.ultimaTrayectoria[-1][0]), int(self.ultimaTrayectoria[-1][1]))
                    else:
                        preSector = (int(self.trayectoria[-1][0]), int(self.trayectoria[-1][1]))
                    postSector = car_position

                    tiempoPost = round(time.time() * 1000, 3)
                    tiempoPre = self.tsect

                    distPre = abs(self.meta[0] - preSector[0])
                    distPost = abs(self.meta[0] - postSector[0])

                    tiempoSector = (distPre * (tiempoPost - tiempoPre)) / (
                            distPre + distPost)  # tiempo desde el punto pre-meta a meta
                    tiempoSector = tiempoPre + tiempoSector  # tiempo en el que se cruzo e sector

                    p = self.sector + 1
                    if p == self.sectores.size / 4:
                        p = 0
                    if self.tiempoSectores[self.sector] != 0:
                        self.tiempoSectores[self.sector] = tiempoSector - self.tiempoSectores[self.sector]
                        self.tiempoSectores[p] = tiempoSector
                    else:
                        self.tiempoSectores[p] = tiempoSector

                    self.sector += 1
                    if self.sector >= self.sectores.size / 4:
                        self.sector = 0
                    self.valorSectorCruzado = self.sector + 1
                    if self.startRace:
                        # se cambia la velocidad a la del nuevo sector
                        vaciar_buffer()

                else:
                    self.tsect = round(time.time() * 1000, 3)
                    self.valorSectorCruzado = 0
        else:
            self.valorSectorCruzado = 0

    def reloadSector(self, car_position):
        distanceMin = None
        sector = None
        initialized = True
        for i in range(0, int((self.sectores.size) / 4)):
            if self.ladoSector[i] == None:
                initialized = False

        if initialized:
            # Es necesario conocer el lado de cada segmento para poder determinar en que sector se encuntra
            # Para ello tendria que haber dado minimo una vuelta al circuito
            for i in range(0, int((self.sectores.size) / 4)):
                distance = math.sqrt(
                    abs(car_position[0] - self.sectores[i, 0]) ** 2 + abs(car_position[1] - self.sectores[i, 1]) ** 2)
                if distanceMin == None or distance < distanceMin:
                    distanceMin = distance
                    sector = i

            # ahora ya conocemos el sector mas próximo
            sectorVector = np.array((self.sectores[sector, 2], self.sectores[sector, 3])) - np.array(
                (self.sectores[sector, 0], self.sectores[sector, 1]))
            carVector = np.array(car_position) - np.array((self.sectores[sector, 2], self.sectores[sector, 3]))
            productoVectorial = np.cross(sectorVector, carVector)

            numSectores = int(self.sectores.size / 4)
            print(f"Numero de sectores: {numSectores} - len: {len(self.sectores)}")

            if self.ladoSector[sector] == True:
                # Si es True es que entra por el lado positivo
                if productoVectorial > 0:
                    # Si el resultado es positivo es que aun no paso el segmento
                    self.sector = sector % numSectores
                else:
                    # si el resultado es negativo, entonces se encuentra del otro lado y por lo tanto en el siguinte sector
                    self.sector = (sector + 1) % numSectores

            else:
                # Si es False es que entra por el lado negativo
                if productoVectorial < 0:
                    # Si el resultado es negativo es que aun no paso el segmento
                    self.sector = sector % numSectores
                else:
                    # si el resultado es positivo, entonces se encuentra del otro lado y por lo tanto en el siguinte sector
                    self.sector = (sector + 1) % numSectores

            print(f"Sector recalculado: {self.sector}")
            vaciar_buffer()




class AlgotirmoVelocidad:
    def __init__(self):
        self.velocidad = [64, 58]
        self.derrapes = []
        self.derrapeEvitado = []
        self.trayectoriaUsada = None
        self.distanceMin = 280
        self.distanceForDerrape = []
        self.indiceDerrape = None  # indice del seiguiente derrape a coger
        self.indiceSegundo = None  # inidca del siguiente fin de derrape a cruzar
        self.enDerrape = False  # inidica si el coche se encuentra en zona de derrape
        self.lastDistance = 0  # ultima distancia calculada
        self.changedVelocity = False  # si ya se cambio la velocidad al llegar a la zona de derrape
        self.tamanoDerrape = []
        # self.derrapeInTrayect = None #indica el punto en la trayectoria al que se aproxima el punto de derrape
        # open("derrapesLog.txt", "w", newline="")
        self.data = []

    def saveData(self, vueltas):
        with open("datosDerrapes.csv", "w", newline="") as archivoCSV:

            columnas = ["vueltas"]
            for point in self.derrapes:
                columnas.append(str(point))

            fichero = csv.writer(archivoCSV)
            fichero.writerow(columnas)
            for i in range(0, len(self.data)):
                if len(self.data[i]) < vueltas + 1:
                    for j in range(len(self.data[i]), vueltas + 1):
                        self.data[i].append(None)

            for i in range(0, vueltas + 1):
                fila = [i]
                for j in range(0, len(self.derrapes)):
                    fila.append(self.data[j][i])
                fichero.writerow(fila)

    def saveLogFile(self, data):
        try:
            with open("derrapesLog.txt", 'a') as log_file:  # 'a' stands for append mode
                log_file.write(data + '\n')  # Adding a new line after each entry
            # print("Data saved successfully to the log file.")
        except IOError as e:
            print(f"Error: {e}")

    def derrapeDetected(self, pos, vuelta, frame):

        self.saveLogFile(f"\n\nDerrape detectado en fotograma número: {frame}")
        # almacena el nuevo derrape detectado

        # para el primer derrape que se detecta
        if self.derrapes == []:
            self.indiceDerrape = 0
            self.indiceSegundo = 0
            self.derrapes.append(pos)
            tamano = self.distancia((pos[0], pos[1]), (pos[2], pos[3]))
            self.tamanoDerrape.append(tamano)
            self.derrapeEvitado.append(vuelta)
            self.distanceForDerrape.append(self.distanceMin)
            self.saveLogFile(
                f"Se trata de un derrape nuevo con tamaño: {tamano} - Punto inicio: ({pos[0]},{pos[1]}) Punto fin: ({pos[2]},{pos[3]})")
            self.data.append([])
            for i in range(0, vuelta):
                self.data[0].append(None)
            self.data[0].append(vuelta)
        else:
            if not self.checkDerrapeCercano(pos, vuelta):
                if self.indiceDerrape == 0:
                    self.derrapes.append(pos)
                    tamano = self.distancia((pos[0], pos[1]), (pos[2], pos[3]))
                    self.tamanoDerrape.append(tamano)
                    self.derrapeEvitado.append(vuelta)
                    self.distanceForDerrape.append(self.distanceMin)
                    self.saveLogFile(
                        f"Se trata de un derrape nuevo con tamaño: {tamano} - Punto inicio: ({pos[0]},{pos[1]}) Punto fin: ({pos[2]},{pos[3]})")
                    self.data.append([])
                    for i in range(0, vuelta):
                        self.data[-1].append(None)
                    self.data[-1].append(vuelta)

                else:
                    self.derrapes.insert(self.indiceDerrape, pos)
                    tamano = self.distancia((pos[0], pos[1]), (pos[2], pos[3]))
                    self.tamanoDerrape.insert(self.indiceDerrape, tamano)
                    self.derrapeEvitado.insert(self.indiceDerrape, vuelta)
                    self.distanceForDerrape.insert(self.indiceDerrape, self.distanceMin)
                    self.saveLogFile(
                        f"Se trata de un derrape nuevo con tamaño: {tamano} - Punto inicio: ({pos[0]},{pos[1]}) Punto fin: ({pos[2]},{pos[3]})")

                    self.data.insert(self.indiceDerrape, [])
                    for i in range(0, vuelta):
                        self.data[self.indiceDerrape].append(None)
                    self.data[self.indiceDerrape].append(vuelta)
                    self.indiceDerrape += 1
                    self.indiceSegundo += 1

        # print(self.indiceDerrape)

        print(self.derrapes)
        self.saveLogFile(f"\nLista de derrapes actualizada: {self.derrapes}")
        print(self.derrapeEvitado)
        print(self.data)

        return self.derrapes

    def checkDerrapeCercano(self, pos, vuelta):
        # indican el derrape del cual es anterior o posterior
        posterior = None  # el derrape ha ocurrido sobre un derrape que empieza antes en la trayectoria, derrape posterior
        anterior = None  # el derrape ha ocurrido sobre un derrape que empieza despues en la trayectoria, derrape anterior
        externo = False
        # self.saveLogFile("Comprobacion de si es uno nuevo o ya existente. Distancias al resto de derrapes ya detectados:")
        for i in range(0, len(self.derrapes)):

            dist11 = self.distancia((pos[0], pos[1]), (self.derrapes[i][0], self.derrapes[i][1]))
            dist12 = self.distancia((pos[0], pos[1]), (self.derrapes[i][2], self.derrapes[i][3]))
            dist21 = self.distancia((pos[2], pos[3]), (self.derrapes[i][0], self.derrapes[i][1]))
            dist22 = self.distancia((pos[2], pos[3]), (self.derrapes[i][2], self.derrapes[i][3]))

            print(f"derrape {i} - {self.tamanoDerrape[i]}: {dist11} {dist12} {dist21} {dist22}")

            if dist21 < 20 and dist22 >= self.tamanoDerrape[i]:
                # si el nuevo derrape acaba cerca del siguiente se unen
                # anteiror -> se alarga hacia el 1 del nuevo derrape
                anterior = (self.indiceDerrape - 1) % len(self.derrapes)
                externo = True
                print(f"ANTERIOR ext {anterior}")

            if dist12 < 20 and dist11 >= self.tamanoDerrape[i]:
                # si el nuevo derrape empieza cerca de donde termina otr se unen
                # posterior -> se alarga hacia el 2 del nuevo derrape
                posterior = (self.indiceDerrape - 1) % len(self.derrapes)
                if posterior == -1:
                    posterior = len(self.derrapes) - 1
                externo = True
                print(f"POSTERIOR ext {posterior}")

            if dist21 <= (self.tamanoDerrape[i] + 8) and dist22 <= (
                    self.tamanoDerrape[i] + 5):  # +5 para añadirle un poco de margen
                # si el nuevo derrape termina dentro de otro
                # anteior -> se alarga hacia el 1 del nuevo derrape
                anterior = (self.indiceDerrape - 1) % len(self.derrapes)
                if anterior == -1:
                    anterior = len(self.derrapes) - 1
                print(f"ANTERIOR {anterior}")

            if dist12 <= (self.tamanoDerrape[i] + 8) and dist11 <= (self.tamanoDerrape[i] + 5):
                # si el nuevo derrape empieza dentro de otro
                posterior = (self.indiceDerrape - 1) % len(self.derrapes)
                if posterior == -1:
                    posterior = len(self.derrapes) - 1
                # posterior -> se alarga hacia el 2 del nuevo derrape
                print(f"POSTERIOR {posterior}")


        if posterior is not None and anterior is not None:
            # derrape que empieza en uno y termina en otro

            if posterior == anterior:
                if externo:
                    # se aumentan ambos límites
                    self.derrapes[posterior][0] = pos[0]
                    self.derrapes[posterior][1] = pos[1]
                    self.derrapes[posterior][2] = pos[2]
                    self.derrapes[posterior][3] = pos[3]

                # empieza y termina en un derrape existente
                self.derrapeEvitado[posterior] = vuelta
                self.distanceForDerrape[posterior] += 20  # se aumenta la distancia
                print(f"derrape {posterior} aumento distancia a {self.distanceForDerrape[posterior]}")
                last = self.data[posterior][-1]
                for j in range(last + 1, vuelta):
                    self.data[posterior].append(None)
                self.data[posterior].append(vuelta)
                print(f"Detro de derrape")
                self.saveLogFile(f"El derrape se encuentra dentro del derrape ya detectado cuyo índice es {posterior}")
                self.saveLogFile(f"Aumento distancia umbral a {self.distanceForDerrape[posterior]}")
                return True

            else:
                posterior = (posterior - 1) % len(self.derrapes)
                # anterior = (anterior - 1) % len(self.derrapes)
                # expandir el primero hasta e segundo y eliminar el segundo
                self.derrapes[posterior][2] = self.derrapes[anterior][2]
                self.derrapes[posterior][3] = self.derrapes[anterior][3]
                self.tamanoDerrape[posterior] = self.distancia(
                    (self.derrapes[posterior][0], self.derrapes[posterior][1]),
                    (self.derrapes[posterior][2], self.derrapes[posterior][3]))
                self.derrapes.pop(anterior)
                self.distanceForDerrape.pop(anterior)
                self.tamanoDerrape.pop(anterior)
                self.derrapeEvitado.pop(vuelta)
                self.derrapeEvitado[posterior] = vuelta
                self.distanceForDerrape[posterior] += 20  # se aumenta la distancia
                print(f"derrape {posterior} aumento distancia a {self.distanceForDerrape[posterior]}")
                print(f"Unión de dos derrapes")
                self.saveLogFile(
                    f"El nuevo derrape ha unido los derrapes numero {posterior} y {anterior} ya existentes en uno único")
                self.saveLogFile(f"Aumento distancia umbral a {self.distanceForDerrape[posterior]}")
                last = self.data[posterior][-1]
                for j in range(last + 1, vuelta):
                    self.data[posterior].append(None)
                self.data[posterior].append(vuelta)

            # ver si son o no el mismo derrape
            return True
        else:
            if posterior is not None:
                # modificar el punto de fin
                self.derrapes[posterior][2] = pos[2]
                self.derrapes[posterior][3] = pos[3]
                # se actualiza la distancia
                self.tamanoDerrape[posterior] = self.distancia(
                    (self.derrapes[posterior][0], self.derrapes[posterior][1]),
                    (self.derrapes[posterior][2], self.derrapes[posterior][3]))
                print(f"Unión derrapes")
                self.saveLogFile(
                    f"El derrape comienza dentro del derrape con indice {posterior}, pero termina fuera de el.\nSe modifica el punto de fin al del nuevo derrape detectado ({pos[2]}, {pos[3]})")
                self.saveLogFile(f"Tamaño del derrape {posterior} actualizado: {self.tamanoDerrape[posterior]}")
                self.derrapeEvitado[posterior] = vuelta
                self.distanceForDerrape[posterior] += 20  # se aumenta la distancia
                self.saveLogFile(f"Aumento distancia umbral a {self.distanceForDerrape[posterior]}")
                print(f"derrape {posterior} aumento distancia a {self.distanceForDerrape[posterior]}")
                last = self.data[posterior][-1]
                for j in range(last + 1, vuelta):
                    self.data[posterior].append(None)
                self.data[posterior].append(vuelta)

                return True
            elif anterior is not None:
                # modificar el punto de inicio
                self.derrapes[anterior][0] = pos[0]
                self.derrapes[anterior][1] = pos[1]
                self.tamanoDerrape[anterior] = self.distancia((self.derrapes[anterior][0], self.derrapes[anterior][1]),
                                                              (self.derrapes[anterior][2], self.derrapes[anterior][3]))
                print(f"Unión derrapes")
                self.saveLogFile(
                    f"El derrape comienza en zona sin derrapes detectados pero termina dentro del derrape con indice {anterior}.\nSe modifica el punto de inicio al del nuevo derrape detectado ({pos[0]}, {pos[1]})")
                self.saveLogFile(f"Tamaño del derrape {anterior} actualizado: {self.tamanoDerrape[anterior]}")
                self.derrapeEvitado[anterior] = vuelta
                self.distanceForDerrape[anterior] += 20  # se aumenta la distancia
                self.saveLogFile(f"Aumento distancia umbral a {self.distanceForDerrape[anterior]}")
                print(f"Derrape {anterior} aumento distancia a {self.distanceForDerrape[anterior]}")
                last = self.data[anterior][-1]
                for j in range(last + 1, vuelta):
                    self.data[anterior].append(None)
                self.data[anterior].append(vuelta)

                return True
            else:
                return False

    def setTrayectoria(self, trayectoria):
        if self.trayectoriaUsada is None:
            self.trayectoriaUsada = np.array(trayectoria)

    def setVelocidad(self, pos, frame):
        velocidad = None
        t = round(time.time() * 1000, 3)

        if self.derrapes == [] or pos == None or frame == None:
            # si pos o frame valen None es por que se acaba de iniciar la carrera
            velocidad = self.velocidad[0]

        if self.trayectoriaUsada is not None and self.trayectoriaUsada.size != 0:

            if self.derrapes != []:

                if not self.enDerrape:
                    # aun no se llego al derrape
                    dist = self.distanceToDerrape(pos, (
                    self.derrapes[self.indiceDerrape][0], self.derrapes[self.indiceDerrape][1]))
                    # print(f"franme: {frame} dist: {dist} ultimaDist: {self.lastDistance} indices: {self.indiceDerrape} - {self.indiceSegundo}")
                    if dist > self.lastDistance:  # Se entra en la zona de derrape
                        print(f"{frame} Punto inicio")
                        self.indiceDerrape += 1
                        self.enDerrape = True
                        self.indiceDerrape = self.indiceDerrape % len(self.derrapes)
                        self.lastDistance = dist
                        if self.changedVelocity:
                            self.changedVelocity = False

                    else:

                        if dist < self.distanceForDerrape[self.indiceDerrape]:
                            # la distancia es menor al umbral
                            # velocidad baja
                            if not self.changedVelocity:
                                self.changedVelocity = True
                                velocidad = self.velocidad[1]
                                arduino.write(('v' + str(self.velocidad[1]) + '\n').encode())
                                print(
                                    f"{frame} BAJAR VELOCIDAD - dist actual: {dist} distancia min: {self.distanceForDerrape[self.indiceDerrape]}")
                        self.lastDistance = dist
                else:
                    # se cruzo el inicio del derrape pero no el fin
                    dist = self.distanceToDerrape(pos, (
                    self.derrapes[self.indiceSegundo][2], self.derrapes[self.indiceSegundo][3]))
                    # print(f"franme: {frame} dist: {dist} ultimaDist: {self.lastDistance} indices: {self.indiceDerrape} - {self.indiceSegundo}")
                    if dist > self.lastDistance:  # el derrape ya se ha superado
                        print("Punto fin")
                        self.indiceSegundo += 1
                        self.enDerrape = False
                        self.indiceSegundo = self.indiceSegundo % len(self.derrapes)

                        # aumentar velocidad
                        velocidad = self.velocidad[0]
                        arduino.write(('v' + str(velocidad) + '\n').encode())
                        print(f"{frame} AUMENTAR VELOCIDAD - {dist}")
                        # CAMBIAR VELOCIDAD
                    self.lastDistance = dist

        y = round(time.time() * 1000, 3) - t

        if self.enDerrape or self.distanceForDerrape == []:
            return None, velocidad
        else:
            return self.distanceForDerrape[self.indiceDerrape], velocidad

    def distanceToDerrape(self, pos, pos2):
        indicePos, indiceDerrape = self.closestPoint(pos, pos2)

        if indicePos < indiceDerrape:
            sumaDistancia = 0
            for i in range(indicePos, indiceDerrape):
                sumaDistancia += self.distancia(self.trayectoriaUsada[i], self.trayectoriaUsada[i + 1])
        elif indicePos == indiceDerrape:
            sumaDistancia = 0
        else:
            sumaDistancia = 0
            fin = self.trayectoriaUsada.shape[0]
            for i in range(indicePos, fin - 1):
                sumaDistancia += self.distancia(self.trayectoriaUsada[i], self.trayectoriaUsada[i + 1])
            for i in range(0, indiceDerrape):
                sumaDistancia += self.distancia(self.trayectoriaUsada[i], self.trayectoriaUsada[i + 1])

        return sumaDistancia

    def closestPoint(self, pos1, pos2):

        diff = self.trayectoriaUsada[:, None] - np.array([pos1, pos2])
        distance_squared = np.sum(diff ** 2, axis=-1)

        # Find the indices of the closest points for each external point
        closest_indices = np.argmin(distance_squared, axis=0)

        return closest_indices[0], closest_indices[1]

    def distancia(self, p1, p2):
        return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


vaciar_buffer()
arduino.write(('v' + str(0) + '\n').encode())
vaciar_buffer()
# Create a window and pass it to the Application object
Aplicacion()

