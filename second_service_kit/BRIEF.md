# Cahier des charges : second service de l'étude de cas

Version 1.0, 2026-10-13. Contact : [à compléter par le premier auteur].

## 1. Contexte

Nous étudions comment vérifier du code écrit par des agents IA. Pour cela, il
nous faut un petit service logiciel avec :
- une **spécification** en langage naturel ;
- une **implémentation de référence** correcte ;
- deux **suites de tests** : une suite visible et une suite cachée ;
- des **fautes injectées** : des versions de la référence qui contiennent chacune un défaut.

Des agents recevront la spécification et devront implémenter le service, puis
le tester. Nous mesurerons ensuite ce que leurs tests détectent.

**Pourquoi on vous le demande à vous.** Nous avons déjà construit un premier
service. Pour que l'étude soit crédible, le second doit être conçu par quelqu'un
qui ne connaît ni nos résultats ni nos hypothèses. Ce document dit tout ce dont
vous avez besoin, et rien de plus.

## 2. Règles d'indépendance (à respecter strictement)

1. Ne consultez ni le dépôt du projet, ni ses résultats, ni ses transcripts.
   N'en discutez pas non plus avec les auteurs avant d'avoir livré. Le kit
   que vous avez reçu suffit.
2. **N'utilisez aucun modèle de langage** (Claude, GPT, Copilot, ni aucun
   autre) pour écrire la spécification, les tests ou les fautes. Les agents
   étudiés sont des modèles de langage, et leur aide créerait une dépendance
   entre la vérité terrain et les sujets de l'étude. Si vous en avez utilisé
   un malgré tout, déclarez-le dans `AUTHOR_NOTES.md`.
3. Choisissez les fautes **pour leur réalisme**, sans chercher à piéger ni à
   favoriser qui que ce soit. Vous ignorez qui doit les détecter, et c'est voulu.

## 3. Le service

- **Domaine : libre**, avec deux exclusions : pas de stockage de documents, et
  pas de paiements. Le service doit avoir un **état** : des utilisateurs ou des
  sessions, des droits d'accès, des ressources partagées, des opérations
  répétées ou concurrentes. Quelques exemples : réservation de créneaux, gestion
  de stock, file de tickets, quotas d'API, prêt de matériel.
- **Taille visée :** environ 10 exigences numérotées, et une implémentation de
  référence de 200 à 400 lignes.
- **Langue :** tout le livrable est en anglais (spécification, code,
  commentaires). Les agents travaillent en anglais.

## 4. Conventions techniques (obligatoires)

- **Python 3.13, bibliothèque standard uniquement**, pour la référence et
  pour tout code qu'un agent devra écrire. Les tests peuvent aussi utiliser
  `hypothesis`.
- **Exécution en processus.** Aucun réseau, aucun fichier, aucune lecture de
  l'heure système, aucun aléa qui influence un résultat attendu.
- Le service est **une classe nommée `Service`** dans un module `solution.py`.
- Chaque méthode publique renvoie un couple `(status, body)` :
  - `status` est un entier dans le style HTTP ;
  - `body` est un `dict`, une `list` ou `None`.
- **Dépendances externes injectées.** Le temps, une passerelle ou un service
  tiers sont passés au constructeur, par exemple `Service(clock, ...)`. Si les
  tests ou le code ont besoin d'importer quelque chose (une exception, un type),
  placez-le dans un **module de support** : un fichier `.py` de plus, que les
  agents pourront importer. Évitez les noms qui existent déjà dans la
  bibliothèque standard.
- **La spécification est un fichier Markdown, `spec.md`**, et ne doit contenir
  **aucun bloc de code délimité par des backticks**. Pour montrer l'interface,
  indentez-la de 4 espaces. Les commentaires `<!-- ... -->` sont retirés avant
  que les agents la lisent, et peuvent servir à vos propres notes.

## 5. Livrables

Un dossier dont la structure suit celle de `example/` :

| Fichier | Contenu |
|---|---|
| `spec.md` | La spécification S, la seule chose que les agents verront avec `T_v`. L'interface doit être complète : signatures, statuts possibles, format des réponses |
| `reference.py` | L'implémentation correcte (elle prendra la place de `solution.py`) |
| modules de support | 0, 1 ou plusieurs fichiers `.py` |
| `visible_tests.py` | **`T_v`** : 5 à 8 tests des cas nominaux. Les agents les verront |
| `hidden_tests.py` | **`T_h`** : la vérité terrain, jamais montrée aux agents. Elle teste chaque exigence de façon approfondie |
| `faults.py` | Les fautes injectées, dans le format de `example/faults.py` |
| `AUTHOR_NOTES.md` | Vos notes : choix faits, points laissés ouverts volontairement, temps passé, outils utilisés |

### Règles pour `S` et `T_h` (les plus importantes)

1. **`T_h` ne teste que ce que `S` fixe.** Si une assertion de `T_h` exige un
   comportement que `S` ne permet pas de déduire, c'est une erreur de
   conception, et elle fausse toute la mesure. Relisez chaque assertion de
   `T_h` en vous demandant : « quelle phrase de `S` impose ceci ? »
2. Si un comportement est **volontairement laissé ouvert**, ne le testez pas,
   et listez-le dans `AUTHOR_NOTES.md`.
3. Écrivez les tests sous forme de fonctions `test_*`, qui importent depuis
   `solution` et utilisent `assert`. N'utilisez pas de fixtures pytest, mais
   les fonctions utilitaires sont permises. Un test doit durer moins de
   10 secondes. Les tests à état sont permis avec
   `hypothesis.stateful.run_state_machine_as_test`, avec des réglages
   déterministes (voir l'exemple).
4. `T_v` doit être assez simple pour que **chaque faute injectée le passe**.
   Sinon, la faute serait triviale à repérer.

### Règles pour les fautes injectées

- **Au moins 12 fautes.** Chacune est **une seule modification locale** de
  `reference.py`, écrite comme un couple (texte d'origine, texte de remplacement).
  Le texte d'origine doit apparaître exactement une fois dans la référence.
- Chaque faute doit **passer `T_v` et échouer sur `T_h`**, et être attrapée par au
  moins un test déterministe : un test à état seul ne suffit pas.
- **Des défauts réalistes**, du genre qu'un développeur compétent pourrait
  commettre. Variez les exigences touchées et les types de défauts.
- Pour chaque faute, indiquez l'exigence qu'elle viole et une courte
  description. Dans `AUTHOR_NOTES.md`, ajoutez une phrase par faute : en quoi
  elle est plausible.

## 6. Validation

Le kit contient `validate.py`. Lancez-le depuis votre dossier :

    python -m pip install pytest hypothesis
    python validate.py

Il vérifie que :
- la référence passe `T_v` et `T_h`, deux fois de suite ;
- chaque faute s'applique, passe `T_v`, échoue sur `T_h` et est attrapée par un test déterministe ;
- `spec.md` ne contient pas de bloc délimité par des backticks ;
- les identifiants de fautes sont uniques.

**La livraison est acceptée quand `validate.py` affiche `ALL OK`.**

Le dossier `example/` contient un service jouet minuscule. Il ne sert qu'à
montrer le format : `cd example`, puis `python ../validate.py --min-faults 2`.

## 7. Après la livraison

Nous intégrerons le service tel quel. Si nous trouvons un problème, nous
vous le signalerons et nous **ne modifierons rien sans votre accord**. Toute
correction sera datée et documentée. Vous serez crédité selon les usages du
projet (à préciser par le premier auteur).
