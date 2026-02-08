async function validateSyllabus(formData) {
    const response = await fetch("/syllabus/validate", {
        method: "POST",
        body: formData
    });

    const data = await response.json();

    if (!data.valid) {
        alert("Invalid syllabus");
        return;
    }

    renderStructuredPreview(data.units);
}

function renderStructuredPreview(units) {
    const container = document.getElementById("structuredPreview");
    container.innerHTML = "";

    units.forEach(unit => {
        const unitTitle = document.createElement("h3");
        unitTitle.innerText = unit.title;
        container.appendChild(unitTitle);

        const ul = document.createElement("ul");
        unit.topics.forEach(topic => {
            const li = document.createElement("li");
            li.innerText = topic.title;
            ul.appendChild(li);
        });

        container.appendChild(ul);
    });

    document.getElementById("confirmBtn").style.display = "block";
}
