// Urban Eredan - logique frontend (vanilla JS, jeu jouable uniquement au clic)
// Version "des par personnage" : plus de Glyphes ; la Puissance et l'Energie d'un
// Combattant proviennent du jet de ses des personnels + des des adverses recus.

const API = "/api";

const ecranSelection = document.getElementById("ecran-selection");
const ecranPartie = document.getElementById("ecran-partie");
const ecranFin = document.getElementById("ecran-fin");

let combattantsDisponibles = [];
const equipeSelectionnee = new Set();
let etatCourant = null;
let catalogueDes = [];

// -------------------------------------------------------------- utilitaires

async function api(path, options) {
  const reponse = await fetch(API + path, options);
  const data = await reponse.json();
  if (!reponse.ok) {
    throw new Error(data.erreur || "Erreur inconnue");
  }
  return data;
}

function vider(el) {
  while (el.firstChild) el.removeChild(el.firstChild);
}

function trouverCombattant(etat, id) {
  return (
    etat.joueur_humain.equipe.find((c) => c.id === id) ||
    etat.joueur_ia.equipe.find((c) => c.id === id)
  );
}

function conditionEstValidee(pouvoir, role, pvSoi, pvAdv) {
  if (!pouvoir) return false;
  switch (pouvoir.condition) {
    case "courage":
      return role === "j1";
    case "riposte":
      return role === "j2";
    case "vengeance":
      return pvAdv > pvSoi;
    case "domination":
      return pvAdv < pvSoi;
    default:
      return false;
  }
}

function rondsEnergie(energie) {
  return Array.from({ length: energie }, () => `<span class="rond-energie"></span>`).join("");
}

function seuilEnergieInfo(energieMin) {
  if (energieMin > 0) {
    return { html: rondsEnergie(energieMin), titre: `Energie ${energieMin} ou plus` };
  }
  return { html: `<span class="rond-energie rond-energie-vide"></span>`, titre: "Toujours actif" };
}

// ------------------------------------------------------------------- des

function nombreCourt(valeur) {
  return Number.isInteger(valeur) ? String(valeur) : valeur.toFixed(1).replace(".", ",");
}

function infobulleDe(de) {
  const faces = de.faces.map((f) => `${f.puissance}/${f.energie}`).join("  ");
  return (
    `${de.libelle} — faces : ${faces}\n` +
    `Moyenne : ${nombreCourt(de.puissance_moyenne)} Puissance / ` +
    `${nombreCourt(de.energie_moyenne)} Energie`
  );
}

/** Pastille d'un de non lance (tel qu'imprime sur une carte Combattant). */
function creerDe(de, classesSup = "") {
  const el = document.createElement("span");
  el.className = `de de-${de.couleur} de-${de.teinte} ${classesSup}`.trim();
  el.title = infobulleDe(de);
  return el;
}

/** Pastille d'un de lance : la Puissance obtenue en gros, l'Energie en ronds. */
function creerDeLance(resultat) {
  const el = document.createElement("span");
  el.className = `de de-lance de-${resultat.couleur} de-${resultat.teinte} origine-${resultat.origine}`;
  el.title =
    `${resultat.libelle} (${resultat.origine === "personnel" ? "de personnel" : "de donne par l'adversaire"})` +
    ` — resultat ${resultat.puissance}/${resultat.energie}`;
  el.innerHTML =
    `<span class="de-puissance">${resultat.puissance}</span>` +
    `<span class="de-energie">${rondsEnergie(resultat.energie)}</span>`;
  return el;
}

function creerListeDes(des, { libelle, classesSup = "" } = {}) {
  const bloc = document.createElement("div");
  bloc.className = "ligne-des";
  if (libelle) {
    const label = document.createElement("span");
    label.className = "ligne-des-libelle";
    label.textContent = libelle;
    bloc.appendChild(label);
  }
  const liste = document.createElement("span");
  liste.className = "ligne-des-liste";
  if (des.length === 0) {
    liste.innerHTML = `<span class="aucun-de">aucun</span>`;
  } else {
    des.forEach((de) => liste.appendChild(creerDe(de, classesSup)));
  }
  bloc.appendChild(liste);
  return bloc;
}

function renderLegende(conteneur) {
  vider(conteneur);
  catalogueDes.forEach((de) => {
    const bloc = document.createElement("div");
    bloc.className = "legende-de";
    bloc.appendChild(creerDe(de));
    const texte = document.createElement("div");
    texte.className = "legende-texte";
    texte.innerHTML =
      `<b>${de.libelle}</b>` +
      `<span class="legende-faces">${de.faces.map((f) => `${f.puissance}/${f.energie}`).join(" · ")}</span>` +
      `<span class="legende-moyenne">moy. ${nombreCourt(de.puissance_moyenne)} Puissance / ` +
      `${nombreCourt(de.energie_moyenne)} Energie</span>`;
    bloc.appendChild(texte);
    conteneur.appendChild(bloc);
  });
}

// --------------------------------------------------------- carte Combattant

function creerCarteCombattant(data, {
  selectionnable = false,
  selectionnee = false,
  active = false,
  conditionValidee = false,
  onClick = null,
  onSurvol = null,
} = {}) {
  const carte = document.createElement("div");
  carte.className = "carte-combattant";
  if (selectionnable) carte.classList.add("selectionnable");
  if (selectionnee) carte.classList.add("selectionnee");
  if (active) carte.classList.add("active-duel");
  if (conditionValidee) carte.classList.add("condition-validee");
  if (data.utilise) carte.classList.add("utilisee");

  const titre = document.createElement("h4");
  titre.textContent = data.nom;
  carte.appendChild(titre);

  const stats = document.createElement("div");
  stats.className = "stats-combattant";
  stats.innerHTML = `<span>Degats <b>${data.degats}</b></span>`;
  carte.appendChild(stats);

  const blocDes = document.createElement("div");
  blocDes.className = "bloc-des";
  blocDes.appendChild(creerListeDes(data.des_personnels, { libelle: "Perso" }));
  blocDes.appendChild(creerListeDes(data.des_adverses, { libelle: "Adverse", classesSup: "de-donne" }));
  carte.appendChild(blocDes);

  const liste = document.createElement("ul");
  liste.className = "liste-pouvoirs";
  if (data.pouvoir) {
    const li = document.createElement("li");
    const seuil = seuilEnergieInfo(data.pouvoir.energie_min);
    li.innerHTML = `<span class="num" title="${seuil.titre}">${seuil.html}</span>${data.pouvoir.description}`;
    liste.appendChild(li);
  }
  carte.appendChild(liste);

  if (data.utilise) {
    const badge = document.createElement("span");
    badge.className = "badge-utilise";
    badge.textContent = "Utilise";
    carte.appendChild(badge);
  }

  if (onClick) carte.addEventListener("click", onClick);
  if (onSurvol) {
    carte.addEventListener("mouseenter", () => onSurvol(data));
    carte.addEventListener("mouseleave", () => onSurvol(null));
  }
  return carte;
}

function formaterDetailListe(detail) {
  if (detail.length === 0) return `<li>0 <span class="detail-label">(aucun de)</span></li>`;
  return detail
    .map(([label, valeur], i) => {
      const texte = i === 0 ? `${valeur}` : `${valeur >= 0 ? "+" : "-"} ${Math.abs(valeur)}`;
      return `<li>${texte} <span class="detail-label">(${label})</span></li>`;
    })
    .join("");
}

// ------------------------------------------------------- ecran de selection

async function initSelectionEcran() {
  const [combattants, des] = await Promise.all([api("/combattants"), api("/des")]);
  combattantsDisponibles = combattants;
  catalogueDes = des;
  renderLegende(document.getElementById("legende-selection"));
  equipeSelectionnee.clear();
  renderGrilleSelection();
}

function renderGrilleSelection() {
  const grille = document.getElementById("grille-selection");
  vider(grille);
  combattantsDisponibles.forEach((c) => {
    const carte = creerCarteCombattant(
      { ...c, utilise: false },
      {
        selectionnable: true,
        selectionnee: equipeSelectionnee.has(c.id),
        onClick: () => toggleSelection(c.id),
      }
    );
    grille.appendChild(carte);
  });
  const compteur = document.getElementById("compteur-selection");
  compteur.textContent = `${equipeSelectionnee.size} / 4 selectionnes`;
  document.getElementById("btn-lancer-partie").disabled = equipeSelectionnee.size !== 4;
}

function toggleSelection(id) {
  if (equipeSelectionnee.has(id)) {
    equipeSelectionnee.delete(id);
  } else if (equipeSelectionnee.size < 4) {
    equipeSelectionnee.add(id);
  }
  renderGrilleSelection();
}

document.getElementById("btn-lancer-partie").addEventListener("click", async () => {
  const etat = await api("/partie", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ equipe: Array.from(equipeSelectionnee) }),
  });
  ecranSelection.classList.add("cache");
  ecranPartie.classList.remove("cache");
  renderLegende(document.getElementById("legende-partie"));
  render(etat);
});

document.getElementById("btn-nouvelle-partie").addEventListener("click", async () => {
  ecranFin.classList.add("cache");
  ecranSelection.classList.remove("cache");
  await initSelectionEcran();
});

// ------------------------------------------------------------- ecran partie

function humanRole(etat) {
  return etat.j1 === "humain" ? "j1" : "j2";
}

function peutChoisirMaintenant(etat) {
  return etat.phase === "choix_combattant" && etat["combattant_" + humanRole(etat)] === null;
}

function combattantIaEngage(etat) {
  const slotIa = humanRole(etat) === "j1" ? "j2" : "j1";
  const id = etat["combattant_" + slotIa];
  return id === null ? null : trouverCombattant(etat, id);
}

function render(etat) {
  etatCourant = etat;
  if (etat.terminee && etat.phase !== "duel_resolu") {
    renderFin(etat);
    return;
  }
  renderTableauBord(etat);
  renderEquipes(etat);
  renderZoneCentrale(etat);
}

function pvRonds(pv) {
  const total = 10;
  const pvSecur = Math.max(0, pv);
  const orangeCount = pvSecur > total ? Math.min(pvSecur - total, total) : 0;
  const pleinCount = pvSecur > total ? total - orangeCount : pvSecur;
  let html = "";
  for (let i = 0; i < total; i++) {
    const classe = i < orangeCount ? "orange" : i < orangeCount + pleinCount ? "plein" : "";
    html += `<span class="pv-rond ${classe}"></span>`;
  }
  return html;
}

function renderTableauBord(etat) {
  const pvH = etat.joueur_humain.pv;
  const pvI = etat.joueur_ia.pv;
  document.getElementById("pv-humain-texte").textContent = `${pvH} PV`;
  document.getElementById("pv-ia-texte").textContent = `${pvI} PV`;
  document.getElementById("pv-humain-ronds").innerHTML = pvRonds(pvH);
  document.getElementById("pv-ia-ronds").innerHTML = pvRonds(pvI);
  document.getElementById("duel-numero-texte").textContent =
    `Duel ${Math.min(etat.duel_numero, etat.duels_max)} / ${etat.duels_max}`;
}

function renderEquipes(etat) {
  const peutChoisir = peutChoisirMaintenant(etat);
  const roleHumain = humanRole(etat);
  const roleIa = roleHumain === "j1" ? "j2" : "j1";

  const grilleHumain = document.getElementById("equipe-humain");
  vider(grilleHumain);
  etat.joueur_humain.equipe.forEach((c) => {
    const active = c.id === etat.combattant_j1 || c.id === etat.combattant_j2;
    const jouable = peutChoisir && !c.utilise;
    grilleHumain.appendChild(
      creerCarteCombattant(c, {
        selectionnable: jouable,
        active,
        conditionValidee: conditionEstValidee(c.pouvoir, roleHumain, etat.joueur_humain.pv, etat.joueur_ia.pv),
        onClick: jouable ? () => soumettreChoix(c.id) : null,
        onSurvol: jouable ? renderApercu : null,
      })
    );
  });

  const grilleIa = document.getElementById("equipe-ia");
  vider(grilleIa);
  etat.joueur_ia.equipe.forEach((c) => {
    const active = c.id === etat.combattant_j1 || c.id === etat.combattant_j2;
    grilleIa.appendChild(
      creerCarteCombattant(c, {
        active,
        conditionValidee: conditionEstValidee(c.pouvoir, roleIa, etat.joueur_ia.pv, etat.joueur_humain.pv),
      })
    );
  });
}

/** Apercu du duel qu'engagerait le Combattant survole : le pool de des qu'il lancerait,
 *  et celui qu'il offrirait a l'adversaire. Si l'IA a deja engage son Combattant (le
 *  joueur est J2), les deux pools sont connus exactement ; sinon on liste les des
 *  adverses que peuvent encore lui donner les Combattants disponibles en face. */
function renderApercu(combattant) {
  const zone = document.getElementById("zone-apercu");
  if (!combattant || !etatCourant || !peutChoisirMaintenant(etatCourant)) {
    zone.classList.add("cache");
    return;
  }
  vider(zone);
  const adverseEngage = combattantIaEngage(etatCourant);

  const titre = document.createElement("p");
  titre.className = "apercu-titre";
  titre.textContent = adverseEngage
    ? `Si tu engages ${combattant.nom} face a ${adverseEngage.nom} :`
    : `Si tu engages ${combattant.nom} :`;
  zone.appendChild(titre);

  const colonnes = document.createElement("div");
  colonnes.className = "apercu-colonnes";

  const moi = document.createElement("div");
  moi.className = "apercu-colonne";
  moi.innerHTML = `<h5>Ton jet</h5>`;
  moi.appendChild(creerListeDes(combattant.des_personnels, { libelle: "Perso" }));
  if (adverseEngage) {
    moi.appendChild(creerListeDes(adverseEngage.des_adverses, { libelle: "Recus" }));
  } else {
    const possibles = etatCourant.joueur_ia.equipe
      .filter((c) => !c.utilise)
      .flatMap((c) => c.des_adverses);
    const uniques = possibles.filter(
      (de, i) => possibles.findIndex((autre) => autre.type === de.type) === i
    );
    moi.appendChild(creerListeDes(uniques, { libelle: "Recus ?" }));
  }
  colonnes.appendChild(moi);

  const lui = document.createElement("div");
  lui.className = "apercu-colonne";
  lui.innerHTML = `<h5>Jet de l'adversaire</h5>`;
  if (adverseEngage) {
    lui.appendChild(creerListeDes(adverseEngage.des_personnels, { libelle: "Perso" }));
  } else {
    const inconnu = creerListeDes([], { libelle: "Perso" });
    inconnu.querySelector(".aucun-de").textContent = "Combattant pas encore engage";
    lui.appendChild(inconnu);
  }
  lui.appendChild(creerListeDes(combattant.des_adverses, { libelle: "Tu donnes", classesSup: "de-donne" }));
  colonnes.appendChild(lui);

  zone.appendChild(colonnes);
  zone.classList.remove("cache");
}

async function soumettreChoix(combattantId) {
  document.getElementById("zone-apercu").classList.add("cache");
  const etat = await api("/partie/combattant", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ combattant_id: combattantId }),
  });
  render(etat);
}

function renderZoneCentrale(etat) {
  const zoneApercu = document.getElementById("zone-apercu");
  const zoneResultat = document.getElementById("zone-resultat");
  const messageAttente = document.getElementById("message-attente");
  const conteneurDuel = document.getElementById("combattants-en-duel");

  zoneApercu.classList.add("cache");
  zoneResultat.classList.add("cache");
  messageAttente.classList.add("cache");
  vider(conteneurDuel);

  const humainSlot = humanRole(etat);
  const iaSlot = humainSlot === "j1" ? "j2" : "j1";
  const humainId = etat["combattant_" + humainSlot];
  const iaId = etat["combattant_" + iaSlot];
  const resultat = etat.dernier_resultat;

  [
    { id: humainId, role: "Toi", slot: humainSlot },
    { id: iaId, role: "IA", slot: iaSlot },
  ].forEach(({ id, role, slot }) => {
    const labelRole = `${role} (${slot.toUpperCase()})`;
    if (id === null) {
      const placeholder = document.createElement("div");
      placeholder.className = "carte-duel";
      placeholder.innerHTML = `<div class="role">${labelRole}</div><h3>En attente...</h3>`;
      conteneurDuel.appendChild(placeholder);
      return;
    }
    const data = trouverCombattant(etat, id);
    const carte = document.createElement("div");
    carte.className = "carte-duel";
    carte.innerHTML = `<div class="role">${labelRole}</div><h3>${data.nom}</h3>`;

    if (resultat) {
      const infoCote =
        resultat.combattant_j1.nom === data.nom ? resultat.combattant_j1 : resultat.combattant_j2;

      const jet = document.createElement("div");
      jet.className = "jet-des";
      infoCote.jet.forEach((de) => jet.appendChild(creerDeLance(de)));
      carte.appendChild(jet);

      const totaux = document.createElement("div");
      totaux.className = "jet-totaux";
      totaux.innerHTML =
        `<span>Des : <b>${infoCote.puissance_des}</b> Puissance</span>` +
        `<span class="jet-energie">Energie : ${rondsEnergie(infoCote.energie) || "<b>0</b>"}</span>`;
      carte.appendChild(totaux);

      // "Seuil atteint" ne dit que l'Energie : la condition du Pouvoir (Courage,
      // Vengeance...) peut encore le recaler, ce que detaille le journal de resolution.
      const seuilAtteint = data.pouvoir && infoCote.energie >= data.pouvoir.energie_min;
      const ligne = document.createElement("div");
      ligne.className = "pouvoir-actif";
      ligne.textContent = seuilAtteint
        ? `Seuil d'Energie atteint : ${data.pouvoir.description}`
        : "Seuil d'Energie non atteint : Pouvoir inactif";
      carte.appendChild(ligne);

      const bloc = document.createElement("div");
      bloc.className = "bloc-stat";
      bloc.innerHTML =
        `<span class="valeur-grosse">${resultat.puissance_finale[data.nom]}</span>` +
        `<span class="libelle-stat">Puissance totale</span>`;
      carte.appendChild(bloc);

      const detail = document.createElement("ul");
      detail.className = "detail-liste";
      detail.innerHTML = formaterDetailListe(resultat.detail_puissance[data.nom]);
      carte.appendChild(detail);

      if (resultat.gagnants.includes(data.nom)) {
        carte.classList.add("gagnant");
        const blocDegats = document.createElement("div");
        blocDegats.className = "bloc-stat degats";
        blocDegats.innerHTML =
          `<span class="valeur-grosse petite">${resultat.degats_finale[data.nom]}</span>` +
          `<span class="libelle-stat">Degats infliges</span>`;
        carte.appendChild(blocDegats);
        const detailDegats = document.createElement("ul");
        detailDegats.className = "detail-liste degats";
        detailDegats.innerHTML = formaterDetailListe(resultat.detail_degats[data.nom]);
        carte.appendChild(detailDegats);
      }
    } else {
      const apercu = document.createElement("div");
      apercu.className = "bloc-des";
      apercu.appendChild(creerListeDes(data.des_personnels, { libelle: "Perso" }));
      apercu.appendChild(creerListeDes(data.des_adverses, { libelle: "Adverse", classesSup: "de-donne" }));
      carte.appendChild(apercu);
    }
    conteneurDuel.appendChild(carte);
  });

  if (etat.phase === "choix_combattant") {
    messageAttente.textContent =
      humainId === null
        ? iaId === null
          ? "Choisis le Combattant que tu engages (tu joues en premier : l'IA repondra en te voyant)."
          : "L'IA a engage son Combattant. Choisis le tien en connaissance de cause."
        : "En attente du choix de l'IA...";
    messageAttente.classList.remove("cache");
  } else if (etat.phase === "duel_resolu") {
    zoneResultat.classList.remove("cache");
    const journal = document.getElementById("journal-resolution");
    vider(journal);
    resultat.log.forEach((ligne) => {
      const p = document.createElement("p");
      if (ligne.includes("remporte le duel")) p.className = "gain";
      p.textContent = ligne;
      journal.appendChild(p);
    });
    const btn = document.getElementById("btn-duel-suivant");
    btn.textContent = etat.terminee ? "Voir le resultat final" : "Duel suivant";
    btn.onclick = etat.terminee ? () => renderFin(etat) : duelSuivant;
  }
}

async function duelSuivant() {
  const etat = await api("/partie/suivant", { method: "POST" });
  render(etat);
}

function renderFin(etat) {
  ecranPartie.classList.add("cache");
  ecranFin.classList.remove("cache");
  const titre = document.getElementById("titre-fin");
  const detail = document.getElementById("detail-fin");
  if (etat.vainqueur === "humain") titre.textContent = "Victoire !";
  else if (etat.vainqueur === "ia") titre.textContent = "Defaite...";
  else titre.textContent = "Egalite";
  detail.textContent = `Toi : ${etat.joueur_humain.pv} PV — IA : ${etat.joueur_ia.pv} PV`;
}

// ------------------------------------------------------------------- start
initSelectionEcran();
