document.addEventListener('DOMContentLoaded', function () {

    console.log("JS chargé OK");

    // =========================
    // AJOUT TÂCHE
    // =========================
    const ajouterBtn = document.getElementById('ajouter-tache');
    const container = document.getElementById('taches-container');

    if (ajouterBtn) {
        ajouterBtn.addEventListener('click', function () {
            container.innerHTML = '';

            const div = document.createElement('div');
            div.className = 'card mb-3';

            div.innerHTML = `
                <div class="card-body">
                    <form method="POST" action="/ajouter-tache">
                        <input type="text" name="description" class="form-control mb-2" placeholder="Description">
                        <button class="btn btn-primary btn-sm">Valider</button>
                    </form>
                </div>
            `;

            container.appendChild(div);
        });
    }

    // =========================
    // DATATABLES
    // =========================
    if (typeof $ !== 'undefined' && $('#table-taches').length) {

        console.log("Init DataTables");

        $('#table-taches').DataTable({
            language: {
                url: 'https://cdn.datatables.net/plug-ins/1.13.6/i18n/fr-FR.json'
            },
            order: [[2, 'desc']],
            columnDefs: [
                { orderable: false, targets: [5] },
                { type: 'date-eu', targets: [3, 4] }
            ]
        });

    } else {
        console.log("DataTables non chargé ou table absente");
    }

});