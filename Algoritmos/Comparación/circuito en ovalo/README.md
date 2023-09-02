Muestra los resultados de la ejecuón del proyecto usando durante las 13 primeras vueltas el algoritmo de velocidad media y durante las 13 siguientes el algoritmo de anticipación a derrape. El objetivo principal es comparar ambos algoritmo en la mismas condiciones para determinar con cual de los dos se obtiene menor tiempo por vuelta.

Tras la ejecución se generaron los siguientes ficheros donde se almacena la información recopilada tras el procesamiento de los fotogramas y la aplicación del algoritmo:

analisisTiemposVuelta1.csv: Contiene los valores de media, desviación típica, valor mínimo y valor máximo para el fichero vueltasAlgAnticipo.csv y vueltasAlgVelcMedia.csv

analisisTiemposVuelta2.csv: Contiene los valores de media, desviación típica, valor mínimo y valor máximo para el fichero vueltasAlgAnticipo.csv y vueltasAlgVelcMedia.csv de las vueltas desde la estabilización de cada algoritmo.

datos.csv: Contiene un registro de diferentes valores y métricas calculadas en el procesamiento de cada frame. Estas son el valor pwm aplicado, si se cruzó la meta, si se cambió de sector, el tiempo por vuelta en caso de haberla cruzado, el momento en el que se obtuvieron los valores, la diferencia de tiempo con el fotograma anterior, la posición d ela etiqueta delantera, la distancia a la posición de la etiqueta delantera del fotograma anterior, si se detectó derrape, la distancia  de la etiqueta trasera a la trayectroia y la posición de la etiqueta trasera.

datosDerrape.csv: Para cada zona de derrape detectada indica en que vueltas se detectó derrape.

derrapes.csv: muestra el número de frame y la distancia a la trayectoria de los fotogramas donde el coche se encontraba derrapando.

derrapesLog.txt: Se trata de un fichero de log donde se indican los eventos ocurridos referidos con los derrapes durante la aplicación del algoritmo de anticipación

vueltasAlgVelcMedia.csv: Almacena en cada línea el tiempo que le llevó al coche recorrer la vuelta completa al circuito cuando la velocidad se determinaba mediante el algoritmo de velocidad media.

vueltasAlgAnticipo.csv: Almacena en cada línea el tiempo que le llevó al coche recorrer la vuelta completa al circuito cuando la velocidad se determinaba mediante el algoritmo de anticipo a derrape.

output.mp4: vídeo de salida donde se muestra la ejecución junto con alguna información sobre la ejecución superpuesta
