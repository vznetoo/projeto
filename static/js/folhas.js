const leafImage = "/static/img/folha.png"; // coloque sua folha aqui

function createLeaf() {
    const leaf = document.createElement("img");
    leaf.src = leafImage;
    leaf.classList.add("leaf");

    // posição horizontal aleatória
    leaf.style.left = Math.random() * 100 + "vw";

    // duração aleatória da animação
    leaf.style.animationDuration = (5 + Math.random() * 5) + "s";

    // tamanho aleatório
    const size = 20 + Math.random() * 40;
    leaf.style.width = size + "px";
    leaf.style.height = size + "px";

    document.getElementById("leaf-container").appendChild(leaf);

    // remove depois de cair
    setTimeout(() => leaf.remove(), 11000);
}

// cria novas folhas continuamente
setInterval(createLeaf, 700);
