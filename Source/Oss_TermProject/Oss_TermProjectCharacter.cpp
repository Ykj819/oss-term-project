// Copyright Epic Games, Inc. All Rights Reserved.

#include "Oss_TermProjectCharacter.h"
#include "Engine/LocalPlayer.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/SpringArmComponent.h"
#include "GameFramework/Controller.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "InputActionValue.h"
#include "InputCoreTypes.h"
#include "InputAction.h"
#include "InputMappingContext.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/RootMotionSource.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimSequenceBase.h"
#include "Animation/AnimSequence.h"
#include "Curves/CurveFloat.h"
#include "TimerManager.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"
#include "Oss_TermProject.h"

AOss_TermProjectCharacter::AOss_TermProjectCharacter()
{
	// Set size for collision capsule
	GetCapsuleComponent()->InitCapsuleSize(42.f, 96.0f);
		
	// Don't rotate when the controller rotates. Let that just affect the camera.
	bUseControllerRotationPitch = false;
	bUseControllerRotationYaw = false;
	bUseControllerRotationRoll = false;

	// Configure character movement
	// Strafe movement: the character keeps facing the camera direction instead of turning toward the movement direction,
	// so S walks backward and A/D sidestep (the anim blueprint picks the directional animations)
	GetCharacterMovement()->bOrientRotationToMovement = false;
	GetCharacterMovement()->bUseControllerDesiredRotation = true;
	GetCharacterMovement()->RotationRate = FRotator(0.0f, 720.0f, 0.0f);

	// Note: For faster iteration times these variables, and many more, can be tweaked in the Character Blueprint
	// instead of recompiling to adjust them
	GetCharacterMovement()->JumpZVelocity = 500.f;
	GetCharacterMovement()->AirControl = 0.35f;
	GetCharacterMovement()->MaxWalkSpeed = WalkSpeed;
	GetCharacterMovement()->MinAnalogWalkSpeed = 20.f;
	GetCharacterMovement()->BrakingDecelerationWalking = 2000.f;
	GetCharacterMovement()->BrakingDecelerationFalling = 1500.0f;

	// Create a camera boom (pulls in towards the player if there is a collision)
	CameraBoom = CreateDefaultSubobject<USpringArmComponent>(TEXT("CameraBoom"));
	CameraBoom->SetupAttachment(RootComponent);
	CameraBoom->TargetArmLength = 400.0f;
	CameraBoom->bUsePawnControlRotation = true;

	// Create a follow camera
	FollowCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("FollowCamera"));
	FollowCamera->SetupAttachment(CameraBoom, USpringArmComponent::SocketName);
	FollowCamera->bUsePawnControlRotation = false;

	// Stick weapon: engine cylinder (100cm tall, 100cm wide, pivot at center) scaled down in code, hidden until equipped
	StickMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("StickMesh"));
	StickMesh->SetupAttachment(GetMesh());
	StickMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	StickMesh->SetGenerateOverlapEvents(false);
	StickMesh->SetHiddenInGame(true);
	static ConstructorHelpers::FObjectFinder<UStaticMesh> CylinderMesh(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
	if (CylinderMesh.Succeeded())
	{
		StickMesh->SetStaticMesh(CylinderMesh.Object);
	}

	// Stick combo: slash A (right-high -> left-low), slash B (left-low -> right-high), repeated
	StickComboAnimations.Add(TSoftObjectPtr<UAnimSequenceBase>(FSoftObjectPath(TEXT("/Game/Characters/Mannequins/Anims/Stick/MM_Stick_Slash_A.MM_Stick_Slash_A"))));
	StickComboAnimations.Add(TSoftObjectPtr<UAnimSequenceBase>(FSoftObjectPath(TEXT("/Game/Characters/Mannequins/Anims/Stick/MM_Stick_Slash_B.MM_Stick_Slash_B"))));
	// when B chains back into A, start A at its wind-up (B already ends with the stick raised)
	StickComboChainStartTimes = { 0.15f, 0.f };

	// Note: The skeletal mesh and anim blueprint references on the Mesh component (inherited from Character) 
	// are set in the derived blueprint asset named ThirdPersonCharacter (to avoid direct content references in C++)
}

void AOss_TermProjectCharacter::BeginPlay()
{
	Super::BeginPlay();

	// apply the (possibly Blueprint-edited) walk speed
	GetCharacterMovement()->MaxWalkSpeed = bIsSprinting ? SprintSpeed : WalkSpeed;

	// roll speed curve: full speed, then ease out at the end
	RollStrengthCurve = NewObject<UCurveFloat>(this, TEXT("RollStrengthCurve"));
	RollStrengthCurve->FloatCurve.AddKey(0.0f, 1.0f);
	RollStrengthCurve->FloatCurve.AddKey(0.7f, 1.0f);
	RollStrengthCurve->FloatCurve.AddKey(1.0f, 0.2f);

	if (RollAnimation.IsNull() || !RollAnimation.LoadSynchronous())
	{
		UE_LOG(LogOss_TermProject, Warning, TEXT("'%s' Roll animation not found (%s). Rolling will move the character without an animation."), *GetNameSafe(this), *RollAnimation.ToString());
	}

	TArray<TSoftObjectPtr<UAnimSequenceBase>*> AttackAnims = { &LightAttackAnimation, &HeavyAttackAnimation, &StickHeavyAttackAnimation };
	for (TSoftObjectPtr<UAnimSequenceBase>& Anim : StickComboAnimations)
	{
		AttackAnims.Add(&Anim);
	}
	for (TSoftObjectPtr<UAnimSequenceBase>* Anim : AttackAnims)
	{
		if (Anim->IsNull() || !Anim->LoadSynchronous())
		{
			UE_LOG(LogOss_TermProject, Warning, TEXT("'%s' Attack animation not found (%s)."), *GetNameSafe(this), *Anim->ToString());
		}
	}

	// the stick attacks step forward through their root bone: make sure root motion extraction is on
	// (same as ticking "Enable Root Motion" on the asset)
	TArray<UAnimSequenceBase*> StickAnims = { StickHeavyAttackAnimation.Get() };
	for (TSoftObjectPtr<UAnimSequenceBase>& Anim : StickComboAnimations)
	{
		StickAnims.Add(Anim.Get());
	}
	for (UAnimSequenceBase* Anim : StickAnims)
	{
		if (UAnimSequence* Sequence = Cast<UAnimSequence>(Anim))
		{
			if (!Sequence->bEnableRootMotion)
			{
				UE_LOG(LogOss_TermProject, Log, TEXT("'%s' Enabling root motion on %s (tick 'Enable Root Motion' on the asset to make this permanent)."), *GetNameSafe(this), *GetNameSafe(Sequence));
				Sequence->bEnableRootMotion = true;
			}
		}
	}

	auto RootDistance = [](const UAnimSequenceBase* Anim) -> float
	{
		return Anim ? Anim->ExtractRootMotionFromRange(0.0, Anim->GetPlayLength(), FAnimExtractContext()).GetTranslation().Size2D() : 0.f;
	};

	// match the stick heavy attack's duration and forward travel to the unarmed charged attack
	StickHeavyPlayRate = 1.f;
	StickHeavyRootMotionScale = 1.f;
	if (bMatchStickHeavyToUnarmed)
	{
		const UAnimSequenceBase* UnarmedHeavy = HeavyAttackAnimation.Get();
		const UAnimSequenceBase* StickHeavy = StickHeavyAttackAnimation.Get();
		if (UnarmedHeavy && StickHeavy && UnarmedHeavy->GetPlayLength() > KINDA_SMALL_NUMBER)
		{
			const float UnarmedDistance = RootDistance(UnarmedHeavy);
			const float StickDistance = RootDistance(StickHeavy);
			StickHeavyPlayRate = StickHeavy->GetPlayLength() / UnarmedHeavy->GetPlayLength();
			StickHeavyRootMotionScale = StickDistance > 1.f ? UnarmedDistance / StickDistance : 1.f;

			UE_LOG(LogOss_TermProject, Log, TEXT("'%s' %s: %.2fs / %.0fcm -> matched to unarmed %.2fs / %.0fcm (play rate %.2f, root motion scale %.2f)"),
				*GetNameSafe(this), *GetNameSafe(StickHeavy), StickHeavy->GetPlayLength(), StickDistance, UnarmedHeavy->GetPlayLength(), UnarmedDistance,
				StickHeavyPlayRate, StickHeavyRootMotionScale);
		}
	}

	// match each slash's duration and forward travel to the unarmed light attack
	StickComboPlayRates.Init(1.f, StickComboAnimations.Num());
	StickComboRootMotionScales.Init(1.f, StickComboAnimations.Num());
	if (bMatchStickAttackToUnarmed)
	{

		const UAnimSequenceBase* Unarmed = LightAttackAnimation.Get();
		const float UnarmedLength = Unarmed ? Unarmed->GetPlayLength() : 0.f;
		const float UnarmedDistance = RootDistance(Unarmed);

		for (int32 i = 0; i < StickComboAnimations.Num(); ++i)
		{
			const UAnimSequenceBase* Slash = StickComboAnimations[i].Get();
			if (!Slash || UnarmedLength <= KINDA_SMALL_NUMBER)
			{
				continue;
			}

			const float SlashDistance = RootDistance(Slash);
			StickComboPlayRates[i] = Slash->GetPlayLength() / UnarmedLength;
			StickComboRootMotionScales[i] = (bMatchStickAttackDistanceToUnarmed && SlashDistance > 1.f) ? UnarmedDistance / SlashDistance : 1.f;

			UE_LOG(LogOss_TermProject, Log, TEXT("'%s' %s: %.2fs / %.0fcm -> matched to unarmed %.2fs / %.0fcm (play rate %.2f, root motion scale %.2f)"),
				*GetNameSafe(this), *GetNameSafe(Slash), Slash->GetPlayLength(), SlashDistance, UnarmedLength, UnarmedDistance,
				StickComboPlayRates[i], StickComboRootMotionScales[i]);
		}
	}
}

void AOss_TermProjectCharacter::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
	// Set up action bindings
	if (UEnhancedInputComponent* EnhancedInputComponent = Cast<UEnhancedInputComponent>(PlayerInputComponent)) {
		
		// Rolling (jumping is disabled; the jump input (Space) rolls instead)
		if (UInputAction* RollInput = RollAction ? RollAction : JumpAction)
		{
			EnhancedInputComponent->BindAction(RollInput, ETriggerEvent::Started, this, &AOss_TermProjectCharacter::DoRoll);
		}

		// Moving
		EnhancedInputComponent->BindAction(MoveAction, ETriggerEvent::Triggered, this, &AOss_TermProjectCharacter::Move);
		EnhancedInputComponent->BindAction(MoveAction, ETriggerEvent::Completed, this, &AOss_TermProjectCharacter::MoveReleased);
		EnhancedInputComponent->BindAction(MoveAction, ETriggerEvent::Canceled, this, &AOss_TermProjectCharacter::MoveReleased);
		EnhancedInputComponent->BindAction(MouseLookAction, ETriggerEvent::Triggered, this, &AOss_TermProjectCharacter::Look);

		// Looking
		EnhancedInputComponent->BindAction(LookAction, ETriggerEvent::Triggered, this, &AOss_TermProjectCharacter::Look);

		// Input actions without an asset assigned are created at runtime and mapped in a code-made mapping context
		auto MakeRuntimeAction = [this](const TCHAR* Name, const FKey& Key) -> UInputAction*
		{
			if (!RuntimeInputMappingContext)
			{
				RuntimeInputMappingContext = NewObject<UInputMappingContext>(this, TEXT("IMC_Runtime"));
			}
			UInputAction* Action = NewObject<UInputAction>(this, Name);
			Action->ValueType = EInputActionValueType::Boolean;
			RuntimeInputMappingContext->MapKey(Action, Key);
			return Action;
		};

		if (!SprintAction)
		{
			SprintAction = MakeRuntimeAction(TEXT("IA_Sprint_Runtime"), EKeys::LeftShift);
		}
		if (!AttackAction)
		{
			AttackAction = MakeRuntimeAction(TEXT("IA_Attack_Runtime"), EKeys::LeftMouseButton);
		}
		if (!EquipStickAction)
		{
			EquipStickAction = MakeRuntimeAction(TEXT("IA_EquipStick_Runtime"), EKeys::One);
		}

		if (RuntimeInputMappingContext)
		{
			if (APlayerController* PC = Cast<APlayerController>(GetController()))
			{
				if (UEnhancedInputLocalPlayerSubsystem* Subsystem = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(PC->GetLocalPlayer()))
				{
					Subsystem->AddMappingContext(RuntimeInputMappingContext, 0);
				}
			}
		}

		// Sprinting
		EnhancedInputComponent->BindAction(SprintAction, ETriggerEvent::Started, this, &AOss_TermProjectCharacter::DoSprintStart);
		EnhancedInputComponent->BindAction(SprintAction, ETriggerEvent::Completed, this, &AOss_TermProjectCharacter::DoSprintEnd);

		// Attacking
		EnhancedInputComponent->BindAction(AttackAction, ETriggerEvent::Started, this, &AOss_TermProjectCharacter::AttackPressed);

		// Equip / unequip the stick
		EnhancedInputComponent->BindAction(EquipStickAction, ETriggerEvent::Started, this, &AOss_TermProjectCharacter::DoToggleStick);
	}
	else
	{
		UE_LOG(LogOss_TermProject, Error, TEXT("'%s' Failed to find an Enhanced Input component! This template is built to use the Enhanced Input system. If you intend to use the legacy system, then you will need to update this C++ file."), *GetNameSafe(this));
	}
}

void AOss_TermProjectCharacter::Move(const FInputActionValue& Value)
{
	// input is a Vector2D
	FVector2D MovementVector = Value.Get<FVector2D>();

	// route the input
	DoMove(MovementVector.X, MovementVector.Y);
}

void AOss_TermProjectCharacter::MoveReleased(const FInputActionValue& Value)
{
	CachedMoveInput = FVector2D::ZeroVector;
}

void AOss_TermProjectCharacter::Look(const FInputActionValue& Value)
{
	// input is a Vector2D
	FVector2D LookAxisVector = Value.Get<FVector2D>();

	// route the input
	DoLook(LookAxisVector.X, LookAxisVector.Y);
}

void AOss_TermProjectCharacter::DoMove(float Right, float Forward)
{
	// remember the held direction so a roll can use it
	CachedMoveInput = FVector2D(Right, Forward);

	// no steering while rolling or attacking
	if (bIsRolling || bIsAttacking)
	{
		return;
	}

	if (GetController() != nullptr)
	{
		// find out which way is forward
		const FRotator Rotation = GetController()->GetControlRotation();
		const FRotator YawRotation(0, Rotation.Yaw, 0);

		// get forward vector
		const FVector ForwardDirection = FRotationMatrix(YawRotation).GetUnitAxis(EAxis::X);

		// get right vector 
		const FVector RightDirection = FRotationMatrix(YawRotation).GetUnitAxis(EAxis::Y);

		// add movement 
		AddMovementInput(ForwardDirection, Forward);
		AddMovementInput(RightDirection, Right);
	}
}

void AOss_TermProjectCharacter::DoLook(float Yaw, float Pitch)
{
	if (GetController() != nullptr)
	{
		// add yaw and pitch input to controller
		AddControllerYawInput(Yaw);
		AddControllerPitchInput(Pitch);

		// turning the camera while it lags behind an attack would orbit around an empty point behind the character:
		// let it catch up so it orbits the character
		if (bIsAttacking && CameraBoom->bEnableCameraLag && (!FMath::IsNearlyZero(Yaw) || !FMath::IsNearlyZero(Pitch)))
		{
			CameraBoom->CameraLagSpeed = AttackCameraCatchUpSpeed;
		}
	}
}

void AOss_TermProjectCharacter::DoJumpStart()
{
	// jumping is disabled; roll instead
	DoRoll();
}

void AOss_TermProjectCharacter::DoJumpEnd()
{
	// jumping is disabled
}

void AOss_TermProjectCharacter::DoRoll()
{
	UCharacterMovementComponent* Movement = GetCharacterMovement();
	if (bIsRolling || bIsAttacking || !Movement->IsMovingOnGround())
	{
		return;
	}

	// roll direction: held input relative to the camera, or the facing direction if no input is held
	FVector RollDir = GetActorForwardVector();
	if (!CachedMoveInput.IsNearlyZero() && GetController())
	{
		const FRotator YawRotation(0.f, GetController()->GetControlRotation().Yaw, 0.f);
		const FRotationMatrix YawMatrix(YawRotation);
		RollDir = YawMatrix.GetUnitAxis(EAxis::X) * CachedMoveInput.Y + YawMatrix.GetUnitAxis(EAxis::Y) * CachedMoveInput.X;
	}
	RollDir.Z = 0.f;
	if (!RollDir.Normalize())
	{
		RollDir = GetActorForwardVector();
	}

	bIsRolling = true;

	// face the roll direction instantly and stop turning toward the camera until the roll ends
	SetActorRotation(RollDir.Rotation());
	Movement->bUseControllerDesiredRotation = false;

	// play the roll animation on the anim blueprint's slot
	float RollDuration = FallbackRollDuration;
	const float BlendOut = 0.15f;
	if (UAnimSequenceBase* Anim = RollAnimation.Get())
	{
		if (UAnimInstance* AnimInstance = GetMesh() ? GetMesh()->GetAnimInstance() : nullptr)
		{
			if (AnimInstance->PlaySlotAnimationAsDynamicMontage(Anim, RollSlotName, 0.1f, BlendOut))
			{
				RollDuration = Anim->GetPlayLength();
			}
		}
	}

	// push the character along the roll direction
	TSharedPtr<FRootMotionSource_ConstantForce> Force = MakeShared<FRootMotionSource_ConstantForce>();
	Force->InstanceName = TEXT("Roll");
	Force->AccumulateMode = ERootMotionAccumulateMode::Override;
	Force->Priority = 500;
	Force->Force = RollDir * RollSpeed;
	Force->Duration = RollDuration * RollMoveFraction;
	Force->StrengthOverTime = RollStrengthCurve;
	Force->Settings.SetFlag(ERootMotionSourceSettingsFlags::IgnoreZAccumulate); // keep gravity
	Force->FinishVelocityParams.Mode = ERootMotionFinishVelocityMode::ClampVelocity;
	Force->FinishVelocityParams.ClampVelocity = WalkSpeed * 0.5f;
	RollRootMotionID = Movement->ApplyRootMotionSource(Force);

	GetWorldTimerManager().SetTimer(RollEndTimer, this, &AOss_TermProjectCharacter::EndRoll, FMath::Max(RollDuration - BlendOut, 0.1f), false);
}

void AOss_TermProjectCharacter::EndRoll()
{
	bIsRolling = false;
	GetCharacterMovement()->bUseControllerDesiredRotation = true;
}

void AOss_TermProjectCharacter::AttackPressed(const FInputActionValue& Value)
{
	// Shift (sprint key) held -> heavy attack
	if (bIsSprinting)
	{
		DoHeavyAttack();
	}
	else
	{
		DoLightAttack();
	}
}

void AOss_TermProjectCharacter::DoLightAttack()
{
	// holding the stick: slash combo instead of the punch
	if (bStickEquipped && StickComboAnimations.Num() > 0)
	{
		StickAttack();
		return;
	}

	PlayAttack(LightAttackAnimation);
}

void AOss_TermProjectCharacter::StickAttack()
{
	if (bIsRolling || !GetCharacterMovement()->IsMovingOnGround())
	{
		return;
	}

	const float Now = GetWorld()->GetTimeSeconds();

	if (bIsAttacking)
	{
		// buffer the next slash once the current one is far enough along (in animation time)
		if (bIsStickAttack && (Now - StickAttackStartTime) * CurrentStickPlayRate >= CurrentStickAttackLength * StickComboInputOpenFraction)
		{
			bStickComboQueued = true;
		}
		return;
	}

	// clicked again shortly after the last slash: continue the combo, otherwise start over
	const bool bContinue = (Now - LastStickAttackEndTime) <= StickComboResetTime;
	PlayStickSlash(bContinue ? NextStickComboIndex : 0, bContinue);
}

bool AOss_TermProjectCharacter::PlayStickSlash(int32 ComboIndex, bool bChained)
{
	if (!StickComboAnimations.IsValidIndex(ComboIndex))
	{
		ComboIndex = 0;
	}

	UAnimSequenceBase* Anim = StickComboAnimations.IsValidIndex(ComboIndex) ? StickComboAnimations[ComboIndex].Get() : nullptr;
	UAnimInstance* AnimInstance = GetMesh() ? GetMesh()->GetAnimInstance() : nullptr;
	if (!Anim || !AnimInstance)
	{
		return false;
	}

	const float Length = Anim->GetPlayLength();
	const float StartTime = (bChained && StickComboChainStartTimes.IsValidIndex(ComboIndex)) ? FMath::Clamp(StickComboChainStartTimes[ComboIndex], 0.f, Length * 0.5f) : 0.f;
	const float PlayRate = FMath::Max((StickComboPlayRates.IsValidIndex(ComboIndex) ? StickComboPlayRates[ComboIndex] : 1.f) * StickAttackSpeedMultiplier, 0.05f);
	const float BlendOut = 0.2f;

	if (!AnimInstance->PlaySlotAnimationAsDynamicMontage(Anim, AttackSlotName, 0.1f, BlendOut, PlayRate, 1, -1.f, StartTime))
	{
		return false;
	}

	// same forward travel as the unarmed attack
	SetAnimRootMotionTranslationScale(StickComboRootMotionScales.IsValidIndex(ComboIndex) ? StickComboRootMotionScales[ComboIndex] : 1.f);

	const float Now = GetWorld()->GetTimeSeconds();
	bIsAttacking = true;
	bIsStickAttack = true;
	bStickComboQueued = false;
	CurrentStickPlayRate = PlayRate;
	StickAttackStartTime = Now - StartTime / PlayRate;
	CurrentStickAttackLength = Length;
	NextStickComboIndex = (ComboIndex + 1) % StickComboAnimations.Num();

	// the first slash faces where the camera is looking; chained slashes keep that facing
	// (snapping to the camera mid-combo spins the character while the camera is lagging behind)
	if (!bChained && GetController())
	{
		SetActorRotation(FRotator(0.f, GetController()->GetControlRotation().Yaw, 0.f));
	}
	GetCharacterMovement()->bUseControllerDesiredRotation = false;
	BeginAttackCamera();

	// timers in real time (animation time / play rate)
	GetWorldTimerManager().SetTimer(StickComboChainTimer, this, &AOss_TermProjectCharacter::OnStickComboChainPoint, FMath::Max((Length * StickComboChainFraction - StartTime) / PlayRate, 0.05f), false);
	GetWorldTimerManager().SetTimer(AttackEndTimer, this, &AOss_TermProjectCharacter::EndAttack, FMath::Max((Length - StartTime) / PlayRate - BlendOut, 0.1f), false);
	return true;
}

void AOss_TermProjectCharacter::OnStickComboChainPoint()
{
	if (bIsAttacking && bIsStickAttack && bStickComboQueued)
	{
		PlayStickSlash(NextStickComboIndex, true);
	}
}

void AOss_TermProjectCharacter::DoHeavyAttack()
{
	// holding the stick: overhead smash instead of the charged punch
	if (bStickEquipped && !StickHeavyAttackAnimation.IsNull())
	{
		if (PlayAttack(StickHeavyAttackAnimation, StickHeavyPlayRate * StickHeavySpeedMultiplier, StickHeavyRootMotionScale))
		{
			// a heavy attack ends the slash combo
			NextStickComboIndex = 0;
			LastStickAttackEndTime = -1000.f;
		}
		return;
	}

	PlayAttack(HeavyAttackAnimation);
}

bool AOss_TermProjectCharacter::PlayAttack(const TSoftObjectPtr<UAnimSequenceBase>& Animation, float PlayRate, float RootMotionScale)
{
	PlayRate = FMath::Max(PlayRate, 0.05f);
	if (bIsAttacking || bIsRolling || !GetCharacterMovement()->IsMovingOnGround())
	{
		return false;
	}

	UAnimSequenceBase* Anim = Animation.Get();
	UAnimInstance* AnimInstance = GetMesh() ? GetMesh()->GetAnimInstance() : nullptr;
	if (!Anim || !AnimInstance)
	{
		return false;
	}

	const float BlendOut = 0.2f;
	if (!AnimInstance->PlaySlotAnimationAsDynamicMontage(Anim, AttackSlotName, 0.1f, BlendOut, PlayRate))
	{
		return false;
	}

	bIsAttacking = true;
	bIsStickAttack = false;
	SetAnimRootMotionTranslationScale(RootMotionScale);

	// attack where the camera is looking, then keep that facing until the attack ends
	if (GetController())
	{
		SetActorRotation(FRotator(0.f, GetController()->GetControlRotation().Yaw, 0.f));
	}
	GetCharacterMovement()->bUseControllerDesiredRotation = false;
	BeginAttackCamera();

	GetWorldTimerManager().SetTimer(AttackEndTimer, this, &AOss_TermProjectCharacter::EndAttack, FMath::Max(Anim->GetPlayLength() / PlayRate - BlendOut, 0.1f), false);
	return true;
}

void AOss_TermProjectCharacter::EndAttack()
{
	// a click buffered after the chain point: continue the combo right away
	if (bIsStickAttack && bStickComboQueued && bStickEquipped && PlayStickSlash(NextStickComboIndex, true))
	{
		return;
	}

	if (bIsStickAttack)
	{
		LastStickAttackEndTime = GetWorld()->GetTimeSeconds();
		SetAnimRootMotionTranslationScale(1.f);
	}

	bIsAttacking = false;
	bIsStickAttack = false;
	bStickComboQueued = false;

	// resume turning toward the camera
	if (!bIsRolling)
	{
		GetCharacterMovement()->bUseControllerDesiredRotation = true;
	}

	EndAttackCamera();
}

void AOss_TermProjectCharacter::BeginAttackCamera()
{
	GetWorldTimerManager().ClearTimer(CameraCatchUpTimer);
	CameraBoom->bEnableCameraLag = true;
	CameraBoom->CameraLagSpeed = AttackCameraLagSpeed;
	CameraBoom->CameraLagMaxDistance = AttackCameraMaxLag;
}

void AOss_TermProjectCharacter::EndAttackCamera()
{
	if (!CameraBoom->bEnableCameraLag)
	{
		return;
	}

	// catch up smoothly, then switch the lag off once the camera is back in place
	CameraBoom->CameraLagSpeed = AttackCameraCatchUpSpeed;
	GetWorldTimerManager().SetTimer(CameraCatchUpTimer, this, &AOss_TermProjectCharacter::ResetAttackCamera, FMath::Max(AttackCameraCatchUpTime, 0.01f), false);
}

void AOss_TermProjectCharacter::ResetAttackCamera()
{
	if (!bIsAttacking)
	{
		CameraBoom->bEnableCameraLag = false;
	}
}

void AOss_TermProjectCharacter::DoToggleStick()
{
	if (bStickEquipped)
	{
		bStickEquipped = false;
		StickMesh->SetHiddenInGame(true);
		return;
	}

	USkeletalMesh* SkelMesh = GetMesh()->GetSkeletalMeshAsset();
	if (!SkelMesh || GetMesh()->GetBoneIndex(StickBoneName) == INDEX_NONE)
	{
		UE_LOG(LogOss_TermProject, Warning, TEXT("'%s' Can't equip stick: bone '%s' not found."), *GetNameSafe(this), *StickBoneName.ToString());
		return;
	}

	// work out the grip in the reference pose, so the result doesn't depend on the current animation
	const FReferenceSkeleton& RefSkel = SkelMesh->GetRefSkeleton();
	auto RefComponentSpace = [&RefSkel](FName Bone) -> FTransform
	{
		FTransform Result = FTransform::Identity;
		for (int32 Index = RefSkel.FindBoneIndex(Bone); Index != INDEX_NONE; Index = RefSkel.GetParentIndex(Index))
		{
			Result = Result * RefSkel.GetRefBonePose()[Index];
		}
		return Result;
	};

	const FTransform Hand = RefComponentSpace(StickBoneName);
	const FVector Index = RefComponentSpace(TEXT("index_01_r")).GetLocation();
	const FVector Middle = RefComponentSpace(TEXT("middle_01_r")).GetLocation();
	const FVector Pinky = RefComponentSpace(TEXT("pinky_01_r")).GetLocation();

	// the stick runs across the palm along the knuckle line (pinky -> index), gripped near its bottom end
	const FVector Axis = (Index - Pinky).GetSafeNormal();
	const FVector Grip = FMath::Lerp(Hand.GetLocation(), Middle, 0.6f);
	const FVector Center = Grip + Axis * (StickLength * 0.5f - StickGripFromEnd);

	// engine cylinder is 100 x 100 x 100 with its length along Z
	const FTransform StickComponentSpace(FRotationMatrix::MakeFromZ(Axis).ToQuat(), Center,
		FVector(StickDiameter / 100.f, StickDiameter / 100.f, StickLength / 100.f));

	StickMesh->AttachToComponent(GetMesh(), FAttachmentTransformRules::SnapToTargetNotIncludingScale, StickBoneName);
	StickMesh->SetRelativeTransform(StickComponentSpace.GetRelativeTransform(Hand));

	// wood-ish color on the engine's basic shape material
	if (UMaterialInstanceDynamic* MID = StickMesh->CreateDynamicMaterialInstance(0))
	{
		MID->SetVectorParameterValue(TEXT("Color"), StickColor);
	}

	StickMesh->SetHiddenInGame(false);
	bStickEquipped = true;
}

void AOss_TermProjectCharacter::DoSprintStart()
{
	bIsSprinting = true;
	GetCharacterMovement()->MaxWalkSpeed = SprintSpeed;
}

void AOss_TermProjectCharacter::DoSprintEnd()
{
	bIsSprinting = false;
	GetCharacterMovement()->MaxWalkSpeed = WalkSpeed;
}
