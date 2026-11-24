// Model swap volume: an invisible box placed in the level. When the (living) player walks into it, the player's body
// becomes NewMesh behind a burst of death smoke (AOss_TermProjectCharacter::ChangeBodyMesh). One way: a player that already
// has NewMesh is left alone; to switch back, place another volume with the old mesh. The look is kept through death and
// saved at bonfires (USoulsSaveGame::BodyMesh).
// NewMesh must use the SK_Mannequin skeleton (default: the user's Tripo knight fitted to it, SKM_HQKnight_Manny).

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ModelSwapVolume.generated.h"

class UBoxComponent;
class USkeletalMesh;

UCLASS()
class AModelSwapVolume : public AActor
{
	GENERATED_BODY()

	/** Trigger area: set its size with Box Extent (half size, cm) */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	UBoxComponent* Box;

public:

	AModelSwapVolume();

protected:

	/** Body the player gets when passing through (must use the SK_Mannequin skeleton) */
	UPROPERTY(EditAnywhere, Category="Model Swap")
	TObjectPtr<USkeletalMesh> NewMesh;

	/** Burst of death smoke at the moment of the swap */
	UPROPERTY(EditAnywhere, Category="Model Swap")
	bool bSmoke = true;

	UFUNCTION()
	void OnBoxBeginOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp,
		int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult);
};
