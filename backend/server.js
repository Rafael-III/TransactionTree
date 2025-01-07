const express = require('express');
const cors = require('cors');
const { spawn } = require('child_process'); // Para ejecutar el script de Python

const app = express();
app.use(cors()); // Permite solicitudes desde el frontend
app.use(express.json()); // Middleware para manejar JSON

// Ruta para procesar texto
app.post('/process', (req, res) => {
    const { text } = req.body; // Recibir el texto desde el frontend

    // Validación del campo 'text'
    if (!text || typeof text !== 'string' || text.trim() === '') {
        // Si el texto no existe, no es una cadena o está vacío
        return res.status(400).json({ error: 'El campo "text" es inválido o está vacío' });
    }

    // Llama al script de Python para procesar el texto
    const pythonProcess = spawn('python', ['../parsing.py', text]);

    let result = '';
    pythonProcess.stdout.on('data', (data) => {
        result += data.toString(); // Captura la salida del script de Python
    });

    pythonProcess.stderr.on('data', (data) => {
        console.error(`Error en el script de Python: ${data}`);
        res.status(500).json({ error: 'Error al procesar el texto' });
    });

    pythonProcess.on('close', () => {
        res.json({ transformed_text: result.trim() }); // Envía el resultado al frontend
    });
});

// Inicia el servidor
const PORT = 5000;
app.listen(PORT, () => {
    console.log(`Backend corriendo en http://localhost:${PORT}`);
});
