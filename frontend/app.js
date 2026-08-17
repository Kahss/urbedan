// Urban Eredan - logique frontend (vanilla JS, jeu jouable uniquement au clic)
// Version "draft de des" : un pool de 6 des est lance au debut de chaque duel, puis les
// deux joueurs y draftent 3 des chacun a tour de role, dans l'ordre des initiatives.

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

/** Pastille d'un de non lance (legende). */
function creerDe(de) {
  const el = document.createElement("span");
  el.className = `de de-${de.couleur}`;
  el.title = infobulleDe(de);
  return el;
}

/** Pastille d'un de lance : la Puissance obtenue en gros, l'Energie en ronds. */
function creerDeLance(resultat, { cliquable = false, onClick = null } = {}) {
  const el = document.createElement("span");
  el.className = `de de-lance de-${resultat.couleur}`;
  if (cliquable) el.classList.add("draftable");
  const rang = resultat.rang_draft ? ` — pris en ${resultat.rang_draft}e` : "";
  el.title = `${resultat.libelle} — resultat ${resultat.puissance}/${resultat.energie}${rang}`;
  el.innerHTML =
    `<span class="de-puissance">${resultat.puissance}</span>` +
    `<span class="de-energie">${rondsEnergie(resultat.energie)}</span>`;
  if (onClick) el.addEventListener("click", onClick);
  return el;
}

function remplirListeDes(conteneur, des, { cliquables = false, onClick = null, vide = "aucun" } = {}) {
  vider(conteneur);
  if (des.length === 0) {
    const rien = document.createElement("span");
    rien.className = "aucun-de";
    rien.textContent = vide;
    conteneur.appendChild(rien);
    return;
  }
  des.forEach((de) => {
    conteneur.appendChild(
      creerDeLance(de, { cliquable: cliquables, onClick: cliquables ? () => onClick(de) : null })
    );
  });
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
  stats.innerHTML =
    `<span title="Determine qui drafte en premier">Initiative <b>${data.initiative}</b></span>` +
    `<span>Degats <b>${data.degats}</b></span>`;
  carte.appendChild(stats);

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
    grille.appendChild(
      creerCarteCombattant(
        { ...c, utilise: false },
        {
          selectionnable: true,
          selectionnee: equipeSelectionnee.has(c.id),
          onClick: () => toggleSelection(c.id),
        }
      )
    );
  });
  document.getElementById("compteur-selection").textContent =
    `${equipeSelectionnee.size} / 4 selectionnes`;
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

function roleIa(etat) {
  return humanRole(etat) === "j1" ? "j2" : "j1";
}

function peutChoisirMaintenant(etat) {
  return etat.phase === "choix_combattant" && etat["combattant_" + humanRole(etat)] === null;
}

function cestMonTourDeDrafter(etat) {
  return etat.phase === "draft" && etat.drafteur_courant === humanRole(etat);
}

function combattantIaEngage(etat) {
  const id = etat["combattant_" + roleIa(etat)];
  return id === null ? null : trouverCombattant(etat, id);
}

function render(etat) {
  etatCourant = etat;
  if (etat.terminee && etat.phase !== "duel_resolu") {
    renderFin(etat);
    return;
  }
  renderTableauBord(etat);
  renderPool(etat);
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
  document.getElementById("pv-humain-texte").textContent = `${etat.joueur_humain.pv} PV`;
  document.getElementById("pv-ia-texte").textContent = `${etat.joueur_ia.pv} PV`;
  document.getElementById("pv-humain-ronds").innerHTML = pvRonds(etat.joueur_humain.pv);
  document.getElementById("pv-ia-ronds").innerHTML = pvRonds(etat.joueur_ia.pv);
  document.getElementById("duel-numero-texte").textContent =
    `Duel ${Math.min(etat.duel_numero, etat.duels_max)} / ${etat.duels_max}`;
}

/** Pool central : les des encore disponibles (cliquables quand c'est au joueur de
 *  drafter) et les des deja pris de chaque cote. */
function renderPool(etat) {
  const monRole = humanRole(etat);
  const monTour = cestMonTourDeDrafter(etat);
  const mesDes = monRole === "j1" ? etat.draft_j1 : etat.draft_j2;
  const desIa = monRole === "j1" ? etat.draft_j2 : etat.draft_j1;

  remplirListeDes(document.getElementById("pool-des"), etat.pool_des, {
    cliquables: monTour,
    onClick: (de) => drafterDe(de.id),
    vide: "pool epuise",
  });
  remplirListeDes(document.getElementById("draft-humain"), mesDes, { vide: "aucun de pris" });
  remplirListeDes(document.getElementById("draft-ia"), desIa, { vide: "aucun de pris" });

  document.getElementById("draft-compte-humain").textContent =
    `${mesDes.length} / ${etat.des_par_joueur}`;
  document.getElementById("draft-compte-ia").textContent =
    `${desIa.length} / ${etat.des_par_joueur}`;

  const consigne = document.getElementById("pool-consigne");
  if (etat.phase === "choix_combattant") {
    consigne.textContent = "Les 6 des sont lances : choisis ton Combattant en connaissance de cause.";
    consigne.className = "pool-consigne";
  } else if (etat.phase === "draft") {
    consigne.textContent = monTour ? "A toi de drafter : clique sur un de." : "L'IA drafte...";
    consigne.className = monTour ? "pool-consigne actif" : "pool-consigne";
  } else {
    consigne.textContent = "Draft termine.";
    consigne.className = "pool-consigne";
  }
}

function renderEquipes(etat) {
  const peutChoisir = peutChoisirMaintenant(etat);
  const roleHumain = humanRole(etat);
  const roleAdverse = roleIa(etat);

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
        conditionValidee: conditionEstValidee(c.pouvoir, roleAdverse, etat.joueur_ia.pv, etat.joueur_humain.pv),
      })
    );
  });
}

/** Apercu au survol : qui drafterait en premier si ce Combattant etait engage. Si l'IA a
 *  deja engage le sien, la reponse est certaine ; sinon on situe l'initiative face aux
 *  Combattants encore disponibles en face. */
function renderApercu(combattant) {
  const zone = document.getElementById("zone-apercu");
  if (!combattant || !etatCourant || !peutChoisirMaintenant(etatCourant)) {
    zone.classList.add("cache");
    return;
  }
  const etat = etatCourant;
  const monRole = humanRole(etat);
  // Regle du spec : la meilleure initiative drafte en premier, J1 l'emporte a egalite.
  const jeDevance = (adverse) =>
    combattant.initiative > adverse.initiative ||
    (combattant.initiative === adverse.initiative && monRole === "j1");

  vider(zone);
  const titre = document.createElement("p");
  titre.className = "apercu-titre";
  titre.textContent = `${combattant.nom} — initiative ${combattant.initiative}`;
  zone.appendChild(titre);

  const detail = document.createElement("p");
  detail.className = "apercu-detail";
  const adverseEngage = combattantIaEngage(etat);
  if (adverseEngage) {
    const premier = jeDevance(adverseEngage);
    detail.innerHTML = premier
      ? `Tu drafterais <b>en premier</b> face a ${adverseEngage.nom} (initiative ${adverseEngage.initiative}).`
      : `${adverseEngage.nom} (initiative ${adverseEngage.initiative}) drafterait <b>en premier</b>.`;
    detail.classList.add(premier ? "favorable" : "defavorable");
  } else {
    const adversaires = etat.joueur_ia.equipe.filter((c) => !c.utilise);
    const devances = adversaires.filter(jeDevance);
    detail.innerHTML =
      `Tu drafterais en premier face a <b>${devances.length}</b> des ${adversaires.length} ` +
      `Combattants encore disponibles en face ` +
      `(${adversaires.map((c) => `${c.nom} ${c.initiative}`).join(", ")}).`;
  }
  zone.appendChild(detail);
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

async function drafterDe(deId) {
  const etat = await api("/partie/draft", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ de_id: deId }),
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
  const iaSlot = roleIa(etat);
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
    const marqueur =
      etat.premier_drafteur === slot ? `<span class="badge-initiative">1er au draft</span>` : "";
    carte.innerHTML =
      `<div class="role">${labelRole}</div><h3>${data.nom}</h3>` +
      `<div class="ligne-initiative">Initiative <b>${data.initiative}</b>${marqueur}</div>`;

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
  } else if (etat.phase === "draft") {
    messageAttente.textContent = cestMonTourDeDrafter(etat)
      ? "Draft en cours : prends un de dans le pool central ci-dessus."
      : "L'IA choisit son de...";
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
