import React, { useState } from 'react';
import './App.css';

const App = () => {
    const [userInput, setUserInput] = useState(`<line>    Family-Owned &amp; Carolinas-Based    </line>
<line>            120 Forum Drive           </line>
<line>          Columbia, SC 29229          </line>
<line>             803-828-6836             </line>
<line></line>
<line>YOUR REWARDS CARD #XXXXXXX7677        </line>
<line>        SPRITE ZERO             8.49 B</line>
<line> 1 @ 2.49                             </line>
<line>SC      SPRITE ZERO             2.49-B</line>
<line>        SPRITE ZERO             8.49 B</line>
<line> 1 @ 2.49                             </line>
<line>SC      SPRITE ZERO             2.49-B</line>
<line>        SANTA CRUZ LIME         5.99 B</line>
<line>        SANTA CRUZ LIME         5.99 B</line>
<line>        KRAFT DRESSING          3.79 B</line>
<line> 1 @ 1.29                             </line>
<line>SC      KRAFT DRESSING          1.29-B</line>
<line>        MENTOS GUM TROPI        4.99 B</line>
<line>        FRITOS CORN CHP         5.89 B</line>
<line>        FRITOS CORN CHP         5.89 B</line>
<line>        MAIN ST.BISTRO B        6.29 B</line>
<line>        FR X AMER BLEND         4.99 B</line>
<line>        ATKINS ENDULGE          6.99 B</line>
<line>        ATKINS ENDULGE          6.99 B</line>
<line>        ATKINS BARS 5CT         6.99 B</line>
<line>        CUCUMBER                3.99 B</line>
<line>   **** SC 2% TAX         1.59        </line>
<line>          **** BALANCE         81.08  </line>
<line></line>
<line>VF      Debit     USD$         81.08  </line>
<line>        Acct # ************9005       </line>
<line>        Authorization # 180365        </line>
<line>        Sequence # 180365             </line>
<line>        APPROVED                      </line>
<line>Contactless                           </line>
<line>* * * PURCHASE * * * PURCHASE * * *   </line>
<line>PIN Verified                          </line>
<line>    Application Label: US Debit       </line>
<line>    AID: A0000000042203               </line>
<line>    TVR: 0000048001                   </line>
<line>    IAD: 0110A040012200000000000000000</line>
<line>    ARC: 3030                         </line>
<line><strong></strong></line>
<line>        CHANGE                   .00  </line>
<line></line>
<line>FRESH REWARDS SAVINGS                 </line>
<line>        Regular Coupons      .00      </line>
<line>        Other Rewards       6.27      </line>
<line><strong>TODAY'S SAVINGS TOTAL:      6.27      </strong></line>
<line></line>
<line></line>
<line></line>
<line></line>
<line>Family-Owned &amp; Carolinas-Based        </line>
<line>We want you to have the best          </line>
<line>homegrown experience around, so       </line>
<line>please tell us about today's          </line>
<line>experience at                         </line>
<line>www.lowesfoods.com/experience         </line>
<line>and then enter our monthly drawing    </line>
<line>to win 1 of 5, $100 LFS gift cards!   </line>
<line>  **************************          </line>
<line>11/13/24 11:02 0276 01 0011 197398    </line>
<line></line>
<line>  Store #276  Manager Jason Torrence  </line>
<line>      Open Daily 6:00am - 10:00pm     </line>
<line></line>
<line></line>
<line></line>`);

    const [transformedText, setTransformedText] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();

        try {
            const response = await fetch('http://127.0.0.1:5000/process', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ text: userInput }),
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
                <h2>Transformar Texto</h2>
                <form onSubmit={handleSubmit}>
                    <textarea
                        value={userInput}
                        onChange={(e) => setUserInput(e.target.value)}
                        rows="30"
                        cols="50"
                        placeholder="Escribe tu texto aquí"
                    />
                    <br />
                    <button type="submit">Enviar</button>
                </form>
            </div>
            <div className="column">
                <h2>Texto Transformado</h2>
                <div className="result-box">{transformedText || 'Aquí aparecerá el texto transformado'}</div>
            </div>
        </div>
    );
};

export default App;
