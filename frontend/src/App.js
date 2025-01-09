import React, { useState } from 'react';
import './App.css';

const App = () => {
    const [userInput, setUserInput] = useState('');
    const [transformedText, setTransformedText] = useState('');
    const [checkboxes, setCheckboxes] = useState({
        extractDataCheckbox: true,
        withoutStaticDataCheckbox: false,
        withoutUnknownDataCheckbox: false,
    });

    const handleCheckboxChange = (e) => {
        const { name, checked } = e.target;
        setCheckboxes({
            ...checkboxes,
            [name]: checked,
        });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        try {
            const response = await fetch('http://127.0.0.1:5000/process', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ text: userInput, checkboxes }),
            });

            const data = await response.json();
            setTransformedText(data.transformed_text);
        } catch (error) {
            console.error('Error:', error);
        }
    };

    return (
        <div className="app-container">
            <div className="column">
                <h2>The transaction</h2>
                <form onSubmit={handleSubmit}>
                    <textarea
                        value={userInput}
                        onChange={(e) => setUserInput(e.target.value)}
                        rows="30"
                        cols="50"
                        placeholder="Write the transaction here"
                    />
                    <div className="checkbox-container">
                        <label>
                            <input
                                type="checkbox"
                                name="extractDataCheckbox"
                                checked={checkboxes.extractDataCheckbox}
                                onChange={handleCheckboxChange}
                            />
                            Extract Data
                        </label>
                        <label>
                            <input
                                type="checkbox"
                                name="withoutStaticDataCheckbox"
                                checked={checkboxes.withoutStaticDataCheckbox}
                                onChange={handleCheckboxChange}
                            />
                            Without static data
                        </label>
                        <label>
                            <input
                                type="checkbox"
                                name="withoutUnknownDataCheckbox"
                                checked={checkboxes.withoutUnknownDataCheckbox}
                                onChange={handleCheckboxChange}
                            />
                            Without unknown data
                        </label>
                    </div>
                    <br />
                    <button type="submit">Extract data</button>
                </form>
            </div>
            <div className="column">
                <h2>Extracted data</h2>
                <div className="result-box">{transformedText || 'Here the extracted data will appear'}</div>
            </div>
        </div>
    );
};

export default App;