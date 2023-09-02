

El archivo datos.csv tiene toda la información obtenida en cada frame. Posiciones de las etiquetas, distancias entre puntos de la trayectoria, distancia a la trayectoria desde la etiqueta trasera, si se consideró derrape. Tambien sobre la carrera, el pwm aplicado, si se curzó la meta o el sector.

datosDerrape.csv contiene para cada derrape detectado en que vueltas se detecteó derrape en dicha zona.

derrapes.csv contiene los valores de distancia de los puntos donde se consideró derrape

derrapes.log contiene los mensajes de log generados en la prueba. Para cada derrape detectado informa si es un derrape nuevo o forma parte de uno ya detectado. Si ya se habia detectado informa si el area de derrape aumenta o no.

algFuncionDerrape.csv contiene los tiempos consumido cuando se ejecutó la función que registra los derrapes del algoritmo

algFuncionDistancia.csv contiene los tiempos de ejecución de la función principal del algoritmo. Esta determina la distancia al siguiente derrape para modificar o no la velocidad.
