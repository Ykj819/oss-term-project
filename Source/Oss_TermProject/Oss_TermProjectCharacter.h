// Copyright Epic Games, Inc. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "Logging/LogMacros.h"
#include "Oss_TermProjectCharacter.generated.h"

class USpringArmComponent;
class UCameraComponent;
class UInputAction;
struct FInputActionValue;

DECLARE_LOG_CATEGORY_EXTERN(LogTemplateCharacter, Log, All);

/**
 *  A simple player-controllable third person character
 *  Implements a controllable orbiting camera
 */
UCLASS(abstract)
class AOss_TermProjectCharacter : public ACharacter
{
	GENERATED_BODY()

	/** Camera boom positioning the camera behind the character */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	USpringArmComponent* CameraBoom;

	/** Follow camera */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	UCameraComponent* FollowCamera;

	/** Stick weapon held in the right hand (hidden until equipped) */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	class UStaticMeshComponent* StickMesh;

	/** Small dot drawn on the locked-on target (hidden while not locked on) */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	class UStaticMeshComponent* LockOnMarker;

	/** Finds and uses interactables (chests, doors, NPCs...) */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	class UInteractionComponent* Interaction;

	/** Health and stamina */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	class UStatsComponent* Stats;

	/** Hit detection for the player's attacks (fists / stick) */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	class UMeleeHitComponent* MeleeHit;

	/** Potion bottle shown in the right hand while drinking */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta = (AllowPrivateAccess = "true"))
	class UStaticMeshComponent* PotionMesh;

	/** Temporary health / stamina bars added to the viewport */
	TSharedPtr<class SWidget> StatsOverlay;

protected:

	/** Jump Input Action (IA_Jump / Space). Jumping is disabled: this action now triggers a roll unless RollAction is set */
	UPROPERTY(EditAnywhere, Category="Input")
	UInputAction* JumpAction;

	/** Roll Input Action (optional; if unset, JumpAction is used) */
	UPROPERTY(EditAnywhere, Category="Input")
	UInputAction* RollAction;

	/** Move Input Action */
	UPROPERTY(EditAnywhere, Category="Input")
	UInputAction* MoveAction;

	/** Look Input Action */
	UPROPERTY(EditAnywhere, Category="Input")
	UInputAction* LookAction;

	/** Mouse Look Input Action */
	UPROPERTY(EditAnywhere, Category="Input")
	UInputAction* MouseLookAction;

	/** Sprint Input Action (optional; if unset, one mapped to Left Shift is created at runtime) */
	UPROPERTY(EditAnywhere, Category="Input")
	UInputAction* SprintAction;

	/** Attack Input Action (optional; if unset, one mapped to Left Mouse Button is created at runtime) */
	UPROPERTY(EditAnywhere, Category="Input")
	UInputAction* AttackAction;

	/** Equip/unequip stick Input Action (optional; if unset, one mapped to the 1 key is created at runtime) */
	UPROPERTY(EditAnywhere, Category="Input")
	UInputAction* EquipStickAction;

	/** Block Input Action (optional; if unset, one mapped to Right Mouse Button is created at runtime) */
	UPROPERTY(EditAnywhere, Category="Input")
	UInputAction* BlockAction;

	/** Lock-on Input Action (optional; if unset, one mapped to Q is created at runtime) */
	UPROPERTY(EditAnywhere, Category="Input")
	UInputAction* LockOnAction;

	/** Interact Input Action (optional; if unset, one mapped to E is created at runtime) */
	UPROPERTY(EditAnywhere, Category="Input")
	UInputAction* InteractAction;

	/** Drink Potion Input Action (optional; if unset, one mapped to R is created at runtime) */
	UPROPERTY(EditAnywhere, Category="Input")
	UInputAction* PotionAction;

	/** Runtime mapping context for input actions created in code (sprint / attack / equip / block / lock-on / interact / potion) */
	UPROPERTY(Transient)
	TObjectPtr<class UInputMappingContext> RuntimeInputMappingContext;

	/** Max walk speed while sprinting */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Movement|Sprint", meta = (ClampMin = 0, Units = "cm/s"))
	float SprintSpeed = 600.f;

	/** Max walk speed while not sprinting */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Movement|Sprint", meta = (ClampMin = 0, Units = "cm/s"))
	float WalkSpeed = 250.f;

	/** True while the sprint input is held */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category="Movement|Sprint")
	bool bIsSprinting = false;

	/** Stamina ran out while sprinting: walk until the sprint key is pressed again */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category="Movement|Sprint")
	bool bSprintExhausted = false;

	/** True while actually running (key held and stamina left) */
	bool IsSprintActive() const;

	/** Stamina used per second while running */
	UPROPERTY(EditAnywhere, Category="Stamina", meta = (ClampMin = 0))
	float SprintStaminaPerSecond = 5.f;

	/** Stamina used by a roll */
	UPROPERTY(EditAnywhere, Category="Stamina", meta = (ClampMin = 0))
	float RollStaminaCost = 10.f;

	/** Stamina used by a light attack (each stick slash too) */
	UPROPERTY(EditAnywhere, Category="Stamina", meta = (ClampMin = 0))
	float LightAttackStaminaCost = 15.f;

	/** Stamina used by a heavy attack */
	UPROPERTY(EditAnywhere, Category="Stamina", meta = (ClampMin = 0))
	float HeavyAttackStaminaCost = 30.f;

	/** Forward roll animation (in place; movement is driven by code) */
	UPROPERTY(EditAnywhere, Category="Movement|Roll")
	TSoftObjectPtr<class UAnimSequenceBase> RollAnimation = TSoftObjectPtr<UAnimSequenceBase>(FSoftObjectPath(TEXT("/Game/Characters/Mannequins/Anims/Unarmed/Roll/MM_Roll_Fwd.MM_Roll_Fwd")));

	/** Anim blueprint slot the roll animation is played on */
	UPROPERTY(EditAnywhere, Category="Movement|Roll")
	FName RollSlotName = TEXT("DefaultSlot");

	/** Horizontal speed during the roll */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Movement|Roll", meta = (ClampMin = 0, Units = "cm/s"))
	float RollSpeed = 500.f;

	/** Fraction of the roll animation during which the character is pushed */
	UPROPERTY(EditAnywhere, Category="Movement|Roll", meta = (ClampMin = 0.1, ClampMax = 1))
	float RollMoveFraction = 0.85f;

	/** Roll duration used when the roll animation can't be loaded */
	UPROPERTY(EditAnywhere, Category="Movement|Roll", meta = (ClampMin = 0.1, Units = "s"))
	float FallbackRollDuration = 0.8f;

	/** True while rolling */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category="Movement|Roll")
	bool bIsRolling = false;

	/** Speed curve over the roll (created at runtime) */
	UPROPERTY(Transient)
	TObjectPtr<class UCurveFloat> RollStrengthCurve;

	/** Last movement input (X = right, Y = forward), cleared when the input is released */
	FVector2D CachedMoveInput = FVector2D::ZeroVector;

	FTimerHandle RollEndTimer;

	uint16 RollRootMotionID = 0;

	/** Light attack animation (Left Mouse Button) */
	UPROPERTY(EditAnywhere, Category="Combat")
	TSoftObjectPtr<class UAnimSequenceBase> LightAttackAnimation = TSoftObjectPtr<UAnimSequenceBase>(FSoftObjectPath(TEXT("/Game/Characters/Mannequins/Anims/Unarmed/Attack/MM_Attack_01.MM_Attack_01")));

	/** Heavy attack animation (Shift + Left Mouse Button) */
	UPROPERTY(EditAnywhere, Category="Combat")
	TSoftObjectPtr<class UAnimSequenceBase> HeavyAttackAnimation = TSoftObjectPtr<UAnimSequenceBase>(FSoftObjectPath(TEXT("/Game/Characters/Mannequins/Anims/Unarmed/Attack/MM_ChargedAttack.MM_ChargedAttack")));

	/** Camera follow speed while attacking (low = camera nearly stays put while the attack lunges forward) */
	UPROPERTY(EditAnywhere, Category="Combat|Camera", meta = (ClampMin = 0.1))
	float AttackCameraLagSpeed = 1.5f;

	/** Camera follow speed used to catch up after the attacks end */
	UPROPERTY(EditAnywhere, Category="Combat|Camera", meta = (ClampMin = 0.1))
	float AttackCameraCatchUpSpeed = 8.f;

	/** How long the camera catches up after the attacks end before normal (lag-free) following resumes */
	UPROPERTY(EditAnywhere, Category="Combat|Camera", meta = (ClampMin = 0, Units = "s"))
	float AttackCameraCatchUpTime = 0.6f;

	/** Max distance the camera may fall behind while attacking */
	UPROPERTY(EditAnywhere, Category="Combat|Camera", meta = (ClampMin = 0, Units = "cm"))
	float AttackCameraMaxLag = 250.f;

	FTimerHandle CameraCatchUpTimer;

	/** Holds the camera (mostly) still while attacking */
	void BeginAttackCamera();

	/** Lets the camera catch up after attacking, then returns to normal following */
	void EndAttackCamera();

	/** Normal following (no lag) */
	void ResetAttackCamera();

	/** Anim blueprint slot the attack animations are played on */
	UPROPERTY(EditAnywhere, Category="Combat")
	FName AttackSlotName = TEXT("DefaultSlot");

	/** Damage of each attack */
	UPROPERTY(EditAnywhere, Category="Combat|Damage", meta = (ClampMin = 0))
	float UnarmedLightDamage = 10.f;

	UPROPERTY(EditAnywhere, Category="Combat|Damage", meta = (ClampMin = 0))
	float UnarmedHeavyDamage = 25.f;

	UPROPERTY(EditAnywhere, Category="Combat|Damage", meta = (ClampMin = 0))
	float StickLightDamage = 15.f;

	UPROPERTY(EditAnywhere, Category="Combat|Damage", meta = (ClampMin = 0))
	float StickHeavyDamage = 35.f;

	/** Part of each attack animation (0..1 of its length) during which it can hit */
	UPROPERTY(EditAnywhere, Category="Combat|Damage")
	FVector2D UnarmedLightHitWindow = FVector2D(0.25f, 0.6f);

	UPROPERTY(EditAnywhere, Category="Combat|Damage")
	FVector2D UnarmedHeavyHitWindow = FVector2D(0.35f, 0.75f);

	UPROPERTY(EditAnywhere, Category="Combat|Damage")
	FVector2D StickSlashHitWindow = FVector2D(0.2f, 0.6f);

	UPROPERTY(EditAnywhere, Category="Combat|Damage")
	FVector2D StickHeavyHitWindow = FVector2D(0.35f, 0.7f);

	/** Fist hit sphere radius */
	UPROPERTY(EditAnywhere, Category="Combat|Damage", meta = (ClampMin = 1, Units = "cm"))
	float FistHitRadius = 18.f;

	/** Stick hit sphere radius */
	UPROPERTY(EditAnywhere, Category="Combat|Damage", meta = (ClampMin = 1, Units = "cm"))
	float StickHitRadius = 8.f;

	FTimerHandle HitWindowStartTimer;
	FTimerHandle HitWindowEndTimer;

	/** Opens the hit window for the part Window (0..1) of an animation of length AnimLength started at StartTime with PlayRate */
	void ScheduleHitWindow(FVector2D Window, float AnimLength, float StartTime, float PlayRate, float Damage, bool bStick);

	/** Closes the hit window and cancels a pending one */
	void CancelHitWindow();

	/** True while an attack animation is playing */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category="Combat")
	bool bIsAttacking = false;

	FTimerHandle AttackEndTimer;

	/** Bone the stick is attached to */
	UPROPERTY(EditAnywhere, Category="Weapon")
	FName StickBoneName = TEXT("hand_r");

	/** Stick length */
	UPROPERTY(EditAnywhere, Category="Weapon", meta = (ClampMin = 1, Units = "cm"))
	float StickLength = 65.f;

	/** Stick thickness */
	UPROPERTY(EditAnywhere, Category="Weapon", meta = (ClampMin = 0.5, Units = "cm"))
	float StickDiameter = 4.f;

	/** How far from the bottom end of the stick the right hand grips it (the left hand grips 13cm below, as authored in the slash animations) */
	UPROPERTY(EditAnywhere, Category="Weapon", meta = (ClampMin = 0, Units = "cm"))
	float StickGripFromEnd = 30.f;

	/** Stick color */
	UPROPERTY(EditAnywhere, Category="Weapon")
	FLinearColor StickColor = FLinearColor(0.25f, 0.13f, 0.05f);

	/** True while the stick is in the hand */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category="Weapon")
	bool bStickEquipped = false;

	/** Stick combo animations, played in order and repeated (Left Mouse Button while the stick is equipped) */
	UPROPERTY(EditAnywhere, Category="Weapon|Combo")
	TArray<TSoftObjectPtr<UAnimSequenceBase>> StickComboAnimations;

	/** Where each combo animation starts when chained from the previous one (s). Lets the 1st slash skip its idle start when looping */
	UPROPERTY(EditAnywhere, Category="Weapon|Combo")
	TArray<float> StickComboChainStartTimes;

	/** Fraction of a slash after which a click is buffered as the next combo attack */
	UPROPERTY(EditAnywhere, Category="Weapon|Combo", meta = (ClampMin = 0, ClampMax = 1))
	float StickComboInputOpenFraction = 0.25f;

	/** Fraction of a slash at which a buffered next attack starts */
	UPROPERTY(EditAnywhere, Category="Weapon|Combo", meta = (ClampMin = 0, ClampMax = 1))
	float StickComboChainFraction = 0.65f;

	/** A click this soon after a slash ends still continues the combo */
	UPROPERTY(EditAnywhere, Category="Weapon|Combo", meta = (ClampMin = 0, Units = "s"))
	float StickComboResetTime = 0.4f;

	/** Stick heavy attack (Shift + Left Mouse Button while the stick is equipped) */
	UPROPERTY(EditAnywhere, Category="Weapon|Heavy")
	TSoftObjectPtr<UAnimSequenceBase> StickHeavyAttackAnimation = TSoftObjectPtr<UAnimSequenceBase>(FSoftObjectPath(TEXT("/Game/Characters/Mannequins/Anims/Stick/MM_Stick_Heavy.MM_Stick_Heavy")));

	/** Play the stick heavy attack with the same duration and forward travel as the unarmed charged attack */
	UPROPERTY(EditAnywhere, Category="Weapon|Heavy")
	bool bMatchStickHeavyToUnarmed = true;

	/** Extra speed on top of the matched timing (1 = same duration as the unarmed charged attack) */
	UPROPERTY(EditAnywhere, Category="Weapon|Heavy", meta = (ClampMin = 0.1))
	float StickHeavySpeedMultiplier = 1.f;

	/** Computed on BeginPlay */
	float StickHeavyPlayRate = 1.f;
	float StickHeavyRootMotionScale = 1.f;

	/** Play each stick slash with the same duration as the unarmed light attack */
	UPROPERTY(EditAnywhere, Category="Weapon|Combo")
	bool bMatchStickAttackToUnarmed = true;

	/** Also scale each slash's forward travel to the unarmed light attack (off = the slash animation's own distance) */
	UPROPERTY(EditAnywhere, Category="Weapon|Combo")
	bool bMatchStickAttackDistanceToUnarmed = false;

	/** Extra speed on top of the unarmed-matched timing (1 = same duration as the unarmed attack) */
	UPROPERTY(EditAnywhere, Category="Weapon|Combo", meta = (ClampMin = 0.1))
	float StickAttackSpeedMultiplier = 1.3f;

	/** Per-slash play rate (computed on BeginPlay) */
	TArray<float> StickComboPlayRates;

	/** Per-slash root motion translation scale (computed on BeginPlay) */
	TArray<float> StickComboRootMotionScales;

	/** Play rate of the current slash */
	float CurrentStickPlayRate = 1.f;

	/** Combo index of the next slash */
	int32 NextStickComboIndex = 0;

	/** True if the current attack is a stick slash */
	bool bIsStickAttack = false;

	/** True if a click was buffered during the current slash */
	bool bStickComboQueued = false;

	/** Time (adjusted for the start offset) the current slash started */
	float StickAttackStartTime = 0.f;

	/** Length of the current slash */
	float CurrentStickAttackLength = 0.f;

	/** Time the last stick slash ended */
	float LastStickAttackEndTime = -1000.f;

	FTimerHandle StickComboChainTimer;

	/** Stick block pose (Right Mouse Button held while the stick is equipped): stick held horizontally in front of the chest */
	UPROPERTY(EditAnywhere, Category="Weapon|Block")
	TSoftObjectPtr<UAnimSequenceBase> StickBlockAnimation = TSoftObjectPtr<UAnimSequenceBase>(FSoftObjectPath(TEXT("/Game/Characters/Mannequins/Anims/Stick/MM_Stick_Block.MM_Stick_Block")));

	/** Time to raise the stick into the block pose */
	UPROPERTY(EditAnywhere, Category="Weapon|Block", meta = (ClampMin = 0, Units = "s"))
	float BlockRaiseTime = 0.12f;

	/** Time to lower the stick when the block is released */
	UPROPERTY(EditAnywhere, Category="Weapon|Block", meta = (ClampMin = 0, Units = "s"))
	float BlockLowerTime = 0.15f;

	/** True while blocking */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category="Weapon|Block")
	bool bIsBlocking = false;

	/** A hit within this time after raising the guard is a perfect block: no stamina, no health lost, no stagger */
	UPROPERTY(EditAnywhere, Category="Weapon|Block", meta = (ClampMin = 0, Units = "s"))
	float PerfectBlockWindow = 0.1f;

	/** Normal block: stamina lost per point of blocked damage (no health lost) */
	UPROPERTY(EditAnywhere, Category="Weapon|Block", meta = (ClampMin = 0))
	float BlockStaminaPerDamage = 1.f;

	/** Normal block: the character is frozen this long */
	UPROPERTY(EditAnywhere, Category="Weapon|Block", meta = (ClampMin = 0, Units = "s"))
	float BlockStaggerTime = 0.4f;

	/** Not enough stamina to block the hit: the guard breaks (still no health lost) and the character is frozen this long */
	UPROPERTY(EditAnywhere, Category="Weapon|Block", meta = (ClampMin = 0, Units = "s"))
	float GuardBreakStaggerTime = 1.f;

	/** Only hits coming from within this angle of the facing direction can be blocked */
	UPROPERTY(EditAnywhere, Category="Weapon|Block", meta = (ClampMin = 0, ClampMax = 180, Units = "deg"))
	float BlockAngle = 90.f;

	/** Time the guard was raised */
	float BlockStartTime = -1000.f;

	/** True while the block button is held (the guard stays up during a block stagger even if released) */
	bool bBlockHeld = false;

	/** Lowers the guard now */
	void StopBlocking();

	/** Roll invincibility starts this long after the roll starts */
	UPROPERTY(EditAnywhere, Category="Movement|Roll", meta = (ClampMin = 0, Units = "s"))
	float RollInvincibleStart = 0.05f;

	/** How long the roll is invincible */
	UPROPERTY(EditAnywhere, Category="Movement|Roll", meta = (ClampMin = 0, Units = "s"))
	float RollInvincibleDuration = 0.4f;

	/** Time the current roll started */
	float RollStartTime = -1000.f;

	/** True during the invincible part of a roll */
	UFUNCTION(BlueprintPure, Category="Combat")
	bool IsInvincible() const;

	/** True while frozen after a block */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category="Combat")
	bool bIsStaggered = false;

	FTimerHandle StaggerTimer;

	/** Freezes the character (no moving, no actions) */
	void StartStagger(float Duration);

	void EndStagger();

	/** True if DamageCauser is in front of the character (within BlockAngle) */
	bool IsInFront(const AActor* DamageCauser) const;

	/** Shows dodge / block results on screen (until there are proper effects) */
	UPROPERTY(EditAnywhere, Category="Combat")
	bool bShowCombatDebugText = true;

	void ShowCombatText(const FString& Text, const FColor& Color) const;

	/** Drinking animation (upper body: right hand from the hip to the mouth) */
	UPROPERTY(EditAnywhere, Category="Potion")
	TSoftObjectPtr<UAnimSequenceBase> PotionAnimation = TSoftObjectPtr<UAnimSequenceBase>(FSoftObjectPath(TEXT("/Game/Characters/Mannequins/Anims/Unarmed/MM_Drink_Potion.MM_Drink_Potion")));

	/** Anim blueprint slot for the drinking animation. Must be an upper-body slot (Layered blend per bone) so the legs keep walking */
	UPROPERTY(EditAnywhere, Category="Potion")
	FName PotionSlotName = TEXT("UpperBody");

	/** Potions per refill */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Potion", meta = (ClampMin = 0))
	int32 MaxPotionCharges = 5;

	/** Potions left */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category="Potion")
	int32 PotionCharges = 5;

	/** Health restored per potion */
	UPROPERTY(EditAnywhere, Category="Potion", meta = (ClampMin = 0))
	float PotionHealAmount = 40.f;

	/** When the health is restored, as a fraction of the animation (the moment the bottle is at the mouth) */
	UPROPERTY(EditAnywhere, Category="Potion", meta = (ClampMin = 0, ClampMax = 1))
	float PotionHealFraction = 0.55f;

	/** Walk speed while drinking (no sprinting) */
	UPROPERTY(EditAnywhere, Category="Potion", meta = (ClampMin = 0, Units = "cm/s"))
	float PotionWalkSpeed = 150.f;

	/** Duration used when the animation can't be loaded */
	UPROPERTY(EditAnywhere, Category="Potion", meta = (ClampMin = 0.1, Units = "s"))
	float FallbackPotionDuration = 1.6f;

	/** Bottle color */
	UPROPERTY(EditAnywhere, Category="Potion")
	FLinearColor PotionColor = FLinearColor(0.9f, 0.45f, 0.05f);

	/** True while drinking */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category="Potion")
	bool bIsDrinking = false;

	FTimerHandle PotionHealTimer;
	FTimerHandle PotionEndTimer;

	/** Bottle reached the mouth */
	void ApplyPotionHeal();

	/** Drinking finished: weapon back in hand */
	void EndDrinkPotion();

	/** Actors with this tag can be locked on to */
	UPROPERTY(EditAnywhere, Category="LockOn")
	FName LockOnTag = TEXT("LockOnTarget");

	/** Max distance to acquire a target */
	UPROPERTY(EditAnywhere, Category="LockOn", meta = (ClampMin = 0, Units = "cm"))
	float LockOnRange = 1500.f;

	/** The lock breaks when the target gets farther than this */
	UPROPERTY(EditAnywhere, Category="LockOn", meta = (ClampMin = 0, Units = "cm"))
	float LockOnBreakDistance = 2000.f;

	/** Only targets within this angle of the camera's view direction are picked */
	UPROPERTY(EditAnywhere, Category="LockOn", meta = (ClampMin = 0, ClampMax = 180, Units = "deg"))
	float LockOnMaxAngle = 60.f;

	/** How fast the camera turns toward the target */
	UPROPERTY(EditAnywhere, Category="LockOn", meta = (ClampMin = 0.1))
	float LockOnCameraSpeed = 8.f;

	/** Extra camera pitch while locked on (negative = look down a bit so the character stays in view) */
	UPROPERTY(EditAnywhere, Category="LockOn", meta = (Units = "deg"))
	float LockOnPitchOffset = -12.f;

	/** How fast the character turns to face the target */
	UPROPERTY(EditAnywhere, Category="LockOn", meta = (ClampMin = 0.1))
	float LockOnTurnSpeed = 12.f;

	/** How much sideways mouse movement (summed over a short moment) switches to the next target */
	UPROPERTY(EditAnywhere, Category="LockOn", meta = (ClampMin = 0.1))
	float LockOnSwitchThreshold = 6.f;

	/** Minimum time between two target switches */
	UPROPERTY(EditAnywhere, Category="LockOn", meta = (ClampMin = 0, Units = "s"))
	float LockOnSwitchCooldown = 0.35f;

	/** Sideways look input summed while locked on (fades out quickly, so only a flick reaches the threshold) */
	float LockOnSwitchInput = 0.f;

	/** Time of the last target switch */
	float LastLockOnSwitchTime = -1000.f;

	/** Switches to the nearest target on the left (Direction < 0) or right (Direction > 0) of the current one on screen */
	void SwitchLockOnTarget(float Direction);

	/** True if the actor can be locked on to: tagged, within Range and visible from the camera */
	bool IsValidLockOnCandidate(AActor* Candidate, float Range) const;

	/** Current lock-on target (null when not locked on) */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category="LockOn")
	TObjectPtr<AActor> LockOnTarget;

	/** Q: lock on to the best target in view, or release the lock */
	void ToggleLockOn();

	/** Picks the target closest to the center of the view (null if none) */
	AActor* FindLockOnTarget() const;

	/** Releases the lock */
	void ClearLockOn();

	/** Center of the target used for aiming the camera */
	FVector GetLockOnPoint(const AActor* Target, float* OutRadius = nullptr) const;

	/** True while rolling, attacking, blocking or staggered */
	bool IsBusy() const { return bIsRolling || bIsAttacking || bIsBlocking || bIsStaggered; }

	/** Sets how the character turns: toward the movement direction normally, toward the target while locked on (unless sprinting), not at all while busy */
	void UpdateRotationMode();

	/** Turns toward the lock-on target, otherwise toward the held movement input (keeps the facing if neither) */
	void FaceActionDirection();

public:

	/** Constructor */
	AOss_TermProjectCharacter();	

protected:

	virtual void BeginPlay() override;

	virtual void Tick(float DeltaSeconds) override;

	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

public:

	/** Damage from ApplyDamage / ApplyPointDamage etc. goes to the stats component */
	virtual float TakeDamage(float DamageAmount, struct FDamageEvent const& DamageEvent, class AController* EventInstigator, AActor* DamageCauser) override;

	/** Returns the stats component */
	FORCEINLINE class UStatsComponent* GetStats() const { return Stats; }

	/** Console (`): DebugDamage 20 */
	UFUNCTION(Exec)
	void DebugDamage(float Amount);

	/** Console (`): DebugRestore -> full health and stamina */
	UFUNCTION(Exec)
	void DebugRestore();

protected:

	/** Initialize input action bindings */
	virtual void SetupPlayerInputComponent(class UInputComponent* PlayerInputComponent) override;

protected:

	/** Called for movement input */
	void Move(const FInputActionValue& Value);

	/** Called when movement input is released */
	void MoveReleased(const FInputActionValue& Value);

	/** Called when the roll finishes */
	void EndRoll();

	/** Called when the attack input is pressed: light attack, or heavy attack while Shift is held */
	void AttackPressed(const FInputActionValue& Value);

	/** Plays an attack animation; returns false if it couldn't start */
	bool PlayAttack(const TSoftObjectPtr<UAnimSequenceBase>& Animation, float StaminaCost, float Damage, FVector2D HitWindow, bool bStick, float PlayRate = 1.f, float RootMotionScale = 1.f);

	/** Health reached 0 */
	UFUNCTION()
	void HandleDeath(AActor* DamageCauser);

	/** Called when the attack animation finishes */
	void EndAttack();

	/** Left click while holding the stick: start / continue the slash combo */
	void StickAttack();

	/** Plays one slash of the stick combo */
	bool PlayStickSlash(int32 ComboIndex, bool bChained);

	/** Reached the chain point of the current slash: start the buffered next one */
	void OnStickComboChainPoint();

	/** Called for looking input */
	void Look(const FInputActionValue& Value);

public:

	/** Handles move inputs from either controls or UI interfaces */
	UFUNCTION(BlueprintCallable, Category="Input")
	virtual void DoMove(float Right, float Forward);

	/** Handles look inputs from either controls or UI interfaces */
	UFUNCTION(BlueprintCallable, Category="Input")
	virtual void DoLook(float Yaw, float Pitch);

	/** Jump is disabled; kept for UI/Blueprint compatibility and rolls instead */
	UFUNCTION(BlueprintCallable, Category="Input")
	virtual void DoJumpStart();

	/** Jump is disabled; does nothing */
	UFUNCTION(BlueprintCallable, Category="Input")
	virtual void DoJumpEnd();

	/** Rolls toward the held movement direction (or forward if none) */
	UFUNCTION(BlueprintCallable, Category="Input")
	virtual void DoRoll();

	/** Plays the light attack */
	UFUNCTION(BlueprintCallable, Category="Input")
	virtual void DoLightAttack();

	/** Plays the heavy attack */
	UFUNCTION(BlueprintCallable, Category="Input")
	virtual void DoHeavyAttack();

	/** Equips the stick in the right hand, or puts it away if already equipped */
	UFUNCTION(BlueprintCallable, Category="Input")
	virtual void DoToggleStick();

	/** Drinks a potion (R): heals, can walk slowly meanwhile, weapon hidden */
	UFUNCTION(BlueprintCallable, Category="Input")
	virtual void DoDrinkPotion();

	/** Refills the potions (e.g. resting at a checkpoint) */
	UFUNCTION(BlueprintCallable, Category="Potion")
	void RefillPotions() { PotionCharges = MaxPotionCharges; }

	UFUNCTION(BlueprintPure, Category="Potion")
	int32 GetPotionCharges() const { return PotionCharges; }

	/** Uses the interactable in front of the character (not while rolling, attacking or blocking) */
	UFUNCTION(BlueprintCallable, Category="Input")
	virtual void DoInteract();

	/** Returns the interaction component */
	FORCEINLINE class UInteractionComponent* GetInteraction() const { return Interaction; }

	/** Raises the stick to block (only while the stick is equipped) */
	UFUNCTION(BlueprintCallable, Category="Input")
	virtual void DoBlockStart();

	/** Lowers the stick */
	UFUNCTION(BlueprintCallable, Category="Input")
	virtual void DoBlockEnd();

	/** Starts sprinting */
	UFUNCTION(BlueprintCallable, Category="Input")
	virtual void DoSprintStart();

	/** Stops sprinting */
	UFUNCTION(BlueprintCallable, Category="Input")
	virtual void DoSprintEnd();

public:

	/** Returns CameraBoom subobject **/
	FORCEINLINE class USpringArmComponent* GetCameraBoom() const { return CameraBoom; }

	/** Returns FollowCamera subobject **/
	FORCEINLINE class UCameraComponent* GetFollowCamera() const { return FollowCamera; }
};

