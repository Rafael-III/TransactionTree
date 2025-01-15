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
    const [inputMode, setInputMode] = useState('database');

    const handleCheckboxChange = (e) => {
        const { name, checked } = e.target;
        setCheckboxes({
            ...checkboxes,
            [name]: checked,
        });
    };

    const handleModeChange = (e) => {
        setInputMode(e.target.value);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        try {
            const response = await fetch('http://127.0.0.1:5000/process', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ text: userInput, checkboxes, mode: inputMode }),
            });

            const data = await response.json();
            console.log(data)
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
                <div className="radio-container">
                        <label>
                            <input
                                type="radio"
                                value="database"
                                checked={inputMode === 'database'}
                                onChange={handleModeChange}
                            />
                            Database
                        </label>
                        <div style={{ marginLeft: '20px', marginTop: '10px' }}>
                            <label style={{ display: 'flex', alignItems: 'center' }}>
                                <span style={{ marginRight: '10px' }}>
                                    Select how many transactions you want to analyze:
                                </span>
                                <input
                                    type="text"
                                    placeholder="0000"
                                    maxLength="4"
                                    style={{
                                        width: '60px', // Ancho del input para 4 dígitos
                                        padding: '5px',
                                        fontSize: '14px',
                                        border: '1px solid #ccc',
                                        borderRadius: '5px',
                                        textAlign: 'center',
                                    }}
                                />
                            </label>
                        </div>
                        <label>
                            <input
                                type="radio"
                                value="onlyOne"
                                checked={inputMode === 'onlyOne'}
                                onChange={handleModeChange}
                            />
                            Only One
                        </label>
                    </div>   
                    <div style={{ marginLeft: '20px', marginTop: '0px' }}>
                        <textarea
                            value={userInput}
                            onChange={(e) => setUserInput(e.target.value)}
                            rows="23"
                            cols="50"
                            placeholder="Write the transaction here"
                        />
                        <div className="checkbox-container" style={{ marginTop: '10px' }}>
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
