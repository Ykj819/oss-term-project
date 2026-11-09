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

	/** Runtime mapping context for input actions created in code (sprint / attack / equip) */
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

public:

	/** Constructor */
	AOss_TermProjectCharacter();	

protected:

	virtual void BeginPlay() override;

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
	bool PlayAttack(const TSoftObjectPtr<UAnimSequenceBase>& Animation, float PlayRate = 1.f, float RootMotionScale = 1.f);

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

