document.addEventListener('DOMContentLoaded', function() {
    function setupTachesManagement() {
        const ajouterTacheBtn = document.getElementById('ajouter-tache');
        if (!ajouterTacheBtn) return;

        ajouterTacheBtn.addEventListener('click', function() {
            const container = document.getElementById('taches-container');
            const newTacheDiv = document.createElement('div');
            newTacheDiv.className = 'tache-input mb-2 d-flex align-items-center';

            const toggleId = 'visibilite-toggle-' + Date.now();

            newTacheDiv.innerHTML = `
                <input type="hidden" name="tache_ids[]" value="">
                <input type="text" class="form-control me-2 flex-grow-1" name="taches[]" placeholder="Description de la tâche" required>
                <input type="date" class="form-control me-2" name="date_limite[]" placeholder="Date limite">
                <select class="form-select me-2" name="statuts[]">
                    <option value="à faire" selected>À faire</option>
                    <option value="en cours">En cours</option>
                    <option value="terminé">Terminé</option>
                </select>
                <input type="hidden" name="visibilites[]" value="prive">
                <div class="form-check form-switch d-flex align-items-center me-2">
                    <input class="form-check-input" type="checkbox" id="${toggleId}">
                    <span class="visibilite-badge ms-2 text-muted">Privé</span>
                </div>
                <button type="button" class="btn btn-sm btn-outline-danger remove-tache">×</button>
            `;
            container.appendChild(newTacheDiv);

            // Gestion de l'interrupteur
            const toggleSwitch = newTacheDiv.querySelector('.form-check-input');
            const visibiliteBadge = newTacheDiv.querySelector('.visibilite-badge');

            toggleSwitch.addEventListener('change', function() {
                const hiddenInput = newTacheDiv.querySelector('input[name="visibilites[]"]');
                if (this.checked) {
                    hiddenInput.value = 'public';
                    visibiliteBadge.textContent = 'Public';
                    visibiliteBadge.classList.add('text-primary');
                    visibiliteBadge.classList.remove('text-muted');
                } else {
                    hiddenInput.value = 'prive';
                    visibiliteBadge.textContent = 'Privé';
                    visibiliteBadge.classList.add('text-muted');
                    visibiliteBadge.classList.remove('text-primary');
                }
            });
        });

        // Gestion de la suppression des tâches
        const tachesContainer = document.getElementById('taches-container');
        if (tachesContainer) {
            tachesContainer.addEventListener('click', function(e) {
                if (e.target.classList.contains('remove-tache') || e.target.closest('.remove-tache')) {
                    e.target.closest('.tache-input').remove();
                }
            });
        }

        // Gestion des interrupteurs existants (pour la première tâche)
        const existingToggles = document.querySelectorAll('.form-check-input');
        existingToggles.forEach(toggle => {
            const visibiliteBadge = toggle.closest('.tache-input').querySelector('.visibilite-badge');
            toggle.addEventListener('change', function() {
                const hiddenInput = toggle.closest('.tache-input').querySelector('input[name="visibilites[]"]');
                if (this.checked) {
                    hiddenInput.value = 'public';
                    visibiliteBadge.textContent = 'Public';
                    visibiliteBadge.classList.add('text-primary');
                    visibiliteBadge.classList.remove('text-muted');
                } else {
                    hiddenInput.value = 'prive';
                    visibiliteBadge.textContent = 'Privé';
                    visibiliteBadge.classList.add('text-muted');
                    visibiliteBadge.classList.remove('text-primary');
                }
            });
        });
    }

    setupTachesManagement();
});
