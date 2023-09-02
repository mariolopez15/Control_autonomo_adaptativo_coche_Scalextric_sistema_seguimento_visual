
En el vídeo se muestra en verde el ROI calculado para cada fotograma procesado. SE muestra que este ROI abarca en todos los casos al coche n su totalidad. Además el  punto amarillo representa el punto extrapolado con el que se calcula el ROI. El punto verde indica el centro del ROI, y está calculado para coincidir con el centro del coche.

Los ficheros genenrados durante la ejecución son los siguientes:


datos.csv: Contiene un registro de diferentes valores y métricas calculadas en el procesamiento de cada frame. Estas son el valor pwm aplicado, si se cruzó la meta, si se cambió de sector, el tiempo por vuelta en caso de haberla cruzado, el momento en el que se obtuvieron los valores, la diferencia de tiempo con el fotograma anterior, la posición d ela etiqueta delantera, la distancia a la posición de la etiqueta delantera del fotograma anterior, si se detectó derrape, la distancia  de la etiqueta trasera a la trayectroia y la posición de la etiqueta trasera. Para este caso a mayores se almacena también el valor del punto extrapolado en cada fotograma.

derrapes.csv: muestra el número de frame y la distancia a la trayectoria de los fotogramas donde el coche se encontraba derrapando.

output.mp4: vídeo de salida con la información superpuesta
