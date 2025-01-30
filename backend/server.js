const express = require('express');
const cors = require('cors');
const { exec, spawn } = require('child_process');

const app = express();
app.use(cors()); // Permite solicitudes desde el frontend
app.use(express.json()); // Middleware para manejar JSON

app.get('/dadabase', (req, res) => {
    exec('python script/dbTest.py', (error, stdout, stderr) => {
        if (error) {
            console.error(`Error ejecutando el script: ${error.message}`);
            return res.status(500).json({ error: "Error ejecutando el script Python" });
        }
        if (stderr) {
            console.error(`Error en el script Python: ${stderr}`);
            return res.status(500).json({ error: "Error en el script Python" });
        }

        try {
            // Convierte la salida (stdout) a JSON y envíala al cliente
            const data = JSON.parse(stdout);
            res.json(data);
        } catch (parseError) {
            console.error(`Error al parsear JSON: ${parseError.message}`);
            res.status(500).json({ error: "Error al parsear la respuesta del script" });
        }
    });
});

app.post('/process', (req, res) => {
    const { text, checkboxes, mode } = req.body;

    // Validación de entrada
    if ((!text || typeof text !== 'string' || text.trim() === '') && mode === 'onlyOne') {
        return res.status(400).json({ error: 'El campo "text" es inválido o está vacío' });
    }

    if (!checkboxes || typeof checkboxes !== 'object') {
        return res.status(400).json({ error: 'El campo "checkboxes" es inválido o está vacío' });
    }

    if (!mode || typeof mode !== 'string' || (mode !== 'database' && mode !== 'onlyOne')) {
        return res.status(400).json({ error: 'El campo "mode" es inválido o está vacío' });
    }

    // Crear un objeto JSON con todos los datos
    const inputData = JSON.stringify({ text, checkboxes, mode });

    // Ejecutar el script de Python
    const pythonProcess = spawn('python', ['../parsing.py']);

    // Escribir los datos en stdin del script
    pythonProcess.stdin.write(inputData);
    pythonProcess.stdin.end();

    let result = '';

    // Leer la salida del script
    pythonProcess.stdout.on('data', (data) => {
        result += data.toString();
    });

    // Manejar errores en el script
    pythonProcess.stderr.on('data', (data) => {
        console.error(`Error en el script de Python: ${data}`);
        res.status(500).json({ error: 'Error al procesar los datos' });
    });

    // Finalizar el proceso
    pythonProcess.on('close', (code) => {
        if (code !== 0) {
            return res.status(500).json({ error: `El script terminó con el código ${code}` });
        }
        res.json({ transformed_text: result.trim() });
    });
});

// Inicia el servidor
const PORT = 5000;
app.listen(PORT, () => {
    console.log(`Backend corriendo en http://localhost:${PORT}`);
});
