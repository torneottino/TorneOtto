document.addEventListener('DOMContentLoaded', function() {
    const selectPercentuale = document.getElementById('percentuale-minima');
    const tabellaClassifica = document.getElementById('classifica-torneo');
    const infoSoglia = document.getElementById('info-soglia');

    if (!selectPercentuale || !tabellaClassifica) return;

    // Funzione per ottenere il numero massimo di presenze
    function getMaxPresenze() {
        const presenze = Array.from(tabellaClassifica.querySelectorAll('tbody tr'))
            .map(row => parseInt(row.cells[3].textContent));
        return Math.max(...presenze);
    }

    // Funzione per calcolare la soglia minima di presenze
    function calcolaSogliaPresenze(percentuale) {
        const maxPresenze = getMaxPresenze();
        return Math.ceil((percentuale / 100) * maxPresenze);
    }

    // Funzione per formattare le celle delle presenze
    function formattaPresenze(row, sogliaMinima) {
        const presenzeCell = row.cells[3];
        const presenze = parseInt(presenzeCell.textContent);
        
        if (presenze >= sogliaMinima) {
            presenzeCell.style.color = '#34c759';
            presenzeCell.style.fontWeight = 'bold';
        } else {
            presenzeCell.style.color = '#ff3b30';
            presenzeCell.style.fontWeight = 'normal';
        }
    }

    // Funzione per aggiornare l'informazione sulla soglia
    function aggiornaInfoSoglia(percentuale) {
        if (percentuale === 0) {
            infoSoglia.style.display = 'none';
            return;
        }

        const maxPresenze = getMaxPresenze();
        const sogliaMinima = calcolaSogliaPresenze(percentuale);
        infoSoglia.textContent = `Soglia minima: ${sogliaMinima} presenze su ${maxPresenze} giornate`;
        infoSoglia.style.display = 'block';
    }

    // Funzione per riordinare la classifica
    function riordinaClassifica(percentuale) {
        const sogliaMinima = calcolaSogliaPresenze(percentuale);
        const tbody = tabellaClassifica.querySelector('tbody');
        const rows = Array.from(tbody.rows);

        // Ripristina l'ordine originale se non c'è filtro
        if (percentuale === 0) {
            rows.forEach(row => formattaPresenze(row, 0));
            return;
        }

        // Dividi i giocatori in due gruppi (sopra e sotto soglia)
        const sopraSoglia = [];
        const sottoSoglia = [];

        rows.forEach(row => {
            const presenze = parseInt(row.cells[3].textContent);
            formattaPresenze(row, sogliaMinima);
            
            if (presenze >= sogliaMinima) {
                sopraSoglia.push(row);
            } else {
                sottoSoglia.push(row);
            }
        });

        // Rimuovi tutte le righe
        while (tbody.firstChild) {
            tbody.removeChild(tbody.firstChild);
        }

        // Aggiungi prima i giocatori sopra soglia, poi quelli sotto soglia
        [...sopraSoglia, ...sottoSoglia].forEach((row, index) => {
            row.cells[0].textContent = index + 1;
            tbody.appendChild(row);
        });
    }

    // Event listener per il cambio di percentuale
    selectPercentuale.addEventListener('change', function() {
        const percentuale = parseInt(this.value);
        aggiornaInfoSoglia(percentuale);
        riordinaClassifica(percentuale);
    });
}); 