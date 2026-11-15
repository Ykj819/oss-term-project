// Club giant: the basic enemy at 1.5x size with a huge two-handed club. Slow, heavy, readable swings; super armor (hits never flinch it).
// Attacks: horizontal sweep (sometimes followed by a backhand sweep) and an overhead slam that sticks in the ground (the opening).
// Animations (mannequin, made in Export/Blender/Club.blend, text 'gen_club.py'): MM_Club_Idle (UpperBody slot loop), MM_Club_Sweep,
// MM_Club_Sweep_Back, MM_Club_Slam. The club grip matches the player's stick contract (knuckle line pinky->index, grip near middle_01).

#pragma once

#include "CoreMinimal.h"
#include "EnemyCharacter.h"
#include "EnemyClub.generated.h"

class UStaticMeshComponent;
class UAnimSequenceBase;

UENUM()
enum class EClubAttack : uint8
{
	None,
	Sweep,
	SweepBack,
	Slam
};

UCLASS()
class AEnemyClub : public AEnemyCharacter
{
	GENERATED_BODY()

	/** Club frame on the right hand: origin = right-hand grip, +Z = along the club toward its head */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	USceneComponent* ClubRoot;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	TArray<UStaticMeshComponent*> ClubParts;

public:

	AEnemyClub();

	virtual void ResetEnemy() override;

protected:

	virtual void BeginPlay() override;

	virtual void TickCombat(APawn* Player, float Distance, float Now, float DeltaSeconds) override;

	virtual void CancelAttack() override;

	// ---- Size / look ----

	/** Size compared to the normal enemy */
	UPROPERTY(EditAnywhere, Category="Enemy|Club Giant", meta = (ClampMin = 0.5))
	float SizeScale = 1.5f;

	UPROPERTY(EditAnywhere, Category="Enemy|Club Giant", meta = (ClampMin = 1))
	float MaxHealth = 200.f;

	UPROPERTY(EditAnywhere, Category="Enemy|Club Giant")
	FLinearColor ClubColor = FLinearColor(0.16f, 0.09f, 0.04f);

	// ---- Club (unscaled mannequin cm; the whole body incl. the club is scaled by SizeScale) ----

	UPROPERTY(EditAnywhere, Category="Enemy|Club Giant|Club", meta = (Units = "cm"))
	float ClubLength = 160.f;

	/** Right hand grips this far from the bottom end (Blender gen_club.py CLUB_GRIP) */
	UPROPERTY(EditAnywhere, Category="Enemy|Club Giant|Club", meta = (Units = "cm"))
	float ClubGripFromEnd = 30.f;

	/** Hit sphere radius along the club (world cm) */
	UPROPERTY(EditAnywhere, Category="Enemy|Club Giant|Club", meta = (Units = "cm"))
	float ClubHitRadius = 24.f;

	// ---- Animations ----

	UPROPERTY(EditAnywhere, Category="Enemy|Club Giant|Animation")
	TSoftObjectPtr<UAnimSequenceBase> IdleAnim;

	UPROPERTY(EditAnywhere, Category="Enemy|Club Giant|Animation")
	TSoftObjectPtr<UAnimSequenceBase> SweepAnim;

	UPROPERTY(EditAnywhere, Category="Enemy|Club Giant|Animation")
	TSoftObjectPtr<UAnimSequenceBase> SweepBackAnim;

	UPROPERTY(EditAnywhere, Category="Enemy|Club Giant|Animation")
	TSoftObjectPtr<UAnimSequenceBase> SlamAnim;

	/** Upper-body slot for the club-holding loop (legs keep walking) */
	UPROPERTY(EditAnywhere, Category="Enemy|Club Giant|Animation")
	FName HoldSlotName = TEXT("UpperBody");

	// ---- Attacks ----

	UPROPERTY(EditAnywhere, Category="Enemy|Club Giant|Attack", meta = (ClampMin = 0))
	float SweepDamage = 30.f;

	UPROPERTY(EditAnywhere, Category="Enemy|Club Giant|Attack", meta = (ClampMin = 0))
	float SlamDamage = 50.f;

	UPROPERTY(EditAnywhere, Category="Enemy|Club Giant|Attack", meta = (ClampMin = 0, ClampMax = 1))
	float SlamChance = 0.3f;

	/** Chance a sweep is followed by the backhand sweep */
	UPROPERTY(EditAnywhere, Category="Enemy|Club Giant|Attack", meta = (ClampMin = 0, ClampMax = 1))
	float ComboChance = 0.35f;

	/** Hit windows (fraction of each animation), from the Blender keys */
	UPROPERTY(EditAnywhere, Category="Enemy|Club Giant|Attack")
	FVector2D SweepHitWindow = FVector2D(0.39f, 0.53f);

	UPROPERTY(EditAnywhere, Category="Enemy|Club Giant|Attack")
	FVector2D SweepBackHitWindow = FVector2D(0.23f, 0.40f);

	UPROPERTY(EditAnywhere, Category="Enemy|Club Giant|Attack")
	FVector2D SlamHitWindow = FVector2D(0.41f, 0.50f);

	/** Keeps turning toward the player until this fraction of each animation (then the swing is committed) */
	UPROPERTY(EditAnywhere, Category="Enemy|Club Giant|Attack")
	float SweepTrackFraction = 0.30f;

	UPROPERTY(EditAnywhere, Category="Enemy|Club Giant|Attack")
	float SweepBackTrackFraction = 0.12f;

	UPROPERTY(EditAnywhere, Category="Enemy|Club Giant|Attack")
	float SlamTrackFraction = 0.36f;

	/** Point of the sweep (fraction) where the backhand follows on (its first frame matches this pose) */
	UPROPERTY(EditAnywhere, Category="Enemy|Club Giant|Attack", meta = (ClampMin = 0, ClampMax = 1))
	float ComboChainFraction = 0.67f;

	// ---- Runtime ----

	EClubAttack CurrentClubAttack = EClubAttack::None;
	bool bComboQueued = false;
	float CurrentTrackTime = 0.f;
	FTimerHandle ComboTimer;

	void StartClubAttack(EClubAttack Attack);

	/** Plays the club-holding loop on the upper body */
	void PlayHoldLoop();

	void AttachClub();
};
