document.addEventListener('DOMContentLoaded', function() {
    const hamburger = document.querySelector('.hamburger');
    const menu = document.querySelector('.menu');
    
    if (hamburger && menu) {
        // Gestione click sull'hamburger
        hamburger.addEventListener('click', function(e) {
            e.stopPropagation(); // Previene la propagazione del click
            hamburger.classList.toggle('active');
            menu.classList.toggle('active');
        });

        // Gestione click fuori dal menu
        document.addEventListener('click', function(e) {
            // Se il menu è attivo e il click è fuori sia dal menu che dall'hamburger
            if (menu.classList.contains('active') && 
                !menu.contains(e.target) && 
                !hamburger.contains(e.target)) {
                hamburger.classList.remove('active');
                menu.classList.remove('active');
            }
        });

        // Previene la chiusura del menu quando si clicca all'interno
        menu.addEventListener('click', function(e) {
            e.stopPropagation();
        });
    }
}); 