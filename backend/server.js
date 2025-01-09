const express = require('express');
const cors = require('cors');
const { spawn } = require('child_process'); // Para ejecutar el script de Python

const app = express();
app.use(cors()); // Permite solicitudes desde el frontend
app.use(express.json()); // Middleware para manejar JSON

// Ruta para procesar texto
app.post('/process', (req, res) => {
    const { text, checkboxes } = req.body; // Recibir texto y checkboxes desde el frontend

    // Validación del campo 'text'
    if (!text || typeof text !== 'string' || text.trim() === '') {
        return res.status(400).json({ error: 'El campo "text" es inválido o está vacío' });
    }

    // Validación del campo 'checkboxes'
    if (!checkboxes || typeof checkboxes !== 'object') {
        return res.status(400).json({ error: 'El campo "checkboxes" es inválido o está vacío' });
    }

    // Convierte los checkboxes a un formato adecuado para el script de Python
    const checkboxesArg = JSON.stringify(checkboxes);

    // Llama al script de Python pasando el texto y los checkboxes como argumentos
    const pythonProcess = spawn('python', ['../parsing.py', text, checkboxesArg]);

    let result = '';
    pythonProcess.stdout.on('data', (data) => {
        result += data.toString();
    });

    pythonProcess.stderr.on('data', (data) => {
        console.error(`Error en el script de Python: ${data}`);
        res.status(500).json({ error: 'Error al procesar el texto y checkboxes' });
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
