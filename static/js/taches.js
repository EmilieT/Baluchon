function setupTachesManagement() {
    const ajouterTacheBtn = document.getElementById('ajouter-tache');
    if (ajouterTacheBtn) {
        ajouterTacheBtn.addEventListener('click', function() {
            const container = document.getElementById('taches-container');
            const newTacheDiv = document.createElement('div');
            newTacheDiv.className = 'tache-input mb-2 d-flex align-items-center';

            newTacheDiv.innerHTML = `
                <input type="hidden" name="tache_ids[]" value="">
                <input type="text" class="form-control me-2 flex-grow-1" name="taches[]" placeholder="Description de la tâche" required>
                <input type="date" class="form-control me-2" name="date_limite[]" placeholder="Date limite">
                <select class="form-select me-2" name="statuts[]">
                    <option value="à faire" selected>À faire</option>
                    <option value="en cours">En cours</option>
                    <option value="terminé">Terminé</option>
                </select>
                <button type="button" class="btn btn-sm btn-outline-danger remove-tache">×</button>
            `;
            container.appendChild(newTacheDiv);
        });
    }

    // Gestion de la suppression des tâches
    const tachesContainer = document.getElementById('taches-container');
    if (tachesContainer) {
        tachesContainer.addEventListener('click', function(e) {
            if (e.target.classList.contains('remove-tache') || e.target.closest('.remove-tache')) {
                e.target.closest('.tache-input').remove();
            }
        });
    }
}

// Appeler la fonction quand le DOM est chargé
document.addEventListener('DOMContentLoaded', setupTachesManagement);
