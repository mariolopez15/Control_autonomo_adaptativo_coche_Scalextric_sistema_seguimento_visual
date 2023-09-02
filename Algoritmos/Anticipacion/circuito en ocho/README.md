Muestra los resultados de la ejecución del sistema empleando el algoritmo de anticipación a derrape sobre un circuito en ocho.

Tras la ejecución se generaron los siguientes ficheros donde se almacena la información recopilada tras el procesamiento de los fotogramas y la aplicación del algoritmo:


datos.csv: Contiene un registro de diferentes valores y métricas calculadas en el procesamiento de cada frame. Estas son el valor pwm aplicado, si se cruzó la meta, si se cambió de sector, el tiempo por vuelta en caso de haberla cruzado, el momento en el que se obtuvieron los valores, la diferencia de tiempo con el fotograma anterior, la posición d ela etiqueta delantera, la distancia a la posición de la etiqueta delantera del fotograma anterior, si se detectó derrape, la distancia  de la etiqueta trasera a la trayectroia y la posición de la etiqueta trasera.

datosDerrape.csv: Para cada zona de derrape detectada indica en que vueltas se detectó derrape.

derrapes.csv: muestra el número de frame y la distancia a la trayectoria de los fotogramas donde el coche se encontraba derrapando.

derrapesLog.txt: Se trata de un fichero de log donde se indican los eventos ocurridos referidos con los derrapes durante la aplicación del algoritmo de anticipación.

algFunionDerrape.csv: Almacena el tiempo de ejecución consumido por la función del algoritmo que registra los derrapes cada vez que se ha ejecutado.

algFuncionDistancia.csv: Almacena el tiempos consumido por la función del algoritmo que calcula las distancias a la zona de derrape.

output.mp4: vídeo de salida donde se muestra la ejecución junto con alguna información sobre la ejecución superpuesta
