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
    const { text, checkboxes, mode } = req.body; // Recibir texto y checkboxes desde el frontend

    // Validación del campo 'text'
    if ((!text || typeof text !== 'string' || text.trim() === '') && mode == 'onlyOne'){
        return res.status(400).json({ error: 'El campo "text" es inválido o está vacío' });
    }

    // Validación del campo 'checkboxes'
    if (!checkboxes || typeof checkboxes !== 'object') {
        return res.status(400).json({ error: 'El campo "checkboxes" es inválido o está vacío' });
    }

    if (!mode || typeof mode !== 'string' || (mode !== 'database' && mode !== 'onlyOne')) {
        return res.status(400).json({ error: 'El campo "mode" es inválido o está vacío' });
    }

    // Convierte los checkboxes a un formato adecuado para el script de Python
    const checkboxesArg = JSON.stringify(checkboxes);

    // Llama al script de Python pasando el texto y los checkboxes como argumentos
    const pythonProcess = spawn('python', ['../parsing.py', text, checkboxesArg, mode]);

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
