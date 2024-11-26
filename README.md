# Support du GamePad

1) Start: Commencer le jeu
2) A: Changer de scène, sortir les pattes d'attérissage
3) D pad: Controle des réacteurs

### Références
#### Code insipirer pour faire l'animation du texte: "Pad 3 please!"
 //coroutine qui joue l'animation du début
    private IEnumerator JouerAnimationDebut()
    {
        float startTime = Time.time;//temps qu'on commence l'animation
        float duration = 2f;//durée de l'animation
        float alphaFin = 1f;//le alpha qu'on souhaite atteindre

        while (Time.time - startTime <= duration)//tant que le temps écouler est moins que la durée
        {
            ChangerABirdViewCam();//on met la caméra au bird view
            float time = (Time.time - startTime) / duration;
            float nouvelleAlpha = Mathf.Lerp(start.alpha, alphaFin, time * 0.03f); //incrémente l'alpha avec lerp
            start.alpha = nouvelleAlpha; //donner la nouvelle alpha

            if (Input.anyKeyDown || Input.GetMouseButtonDown(0))//si on détect un click soit sur le clavier ou la souris, on skip l'animation
            {
                break;
            }

            yield return null;
        }
        activerInput = true;
        start.alpha = alphaFin; 
        start.alpha = 0f; 
        TeleporterPiste(0); 

    }
