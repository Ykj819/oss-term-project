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
#include "EngineUtils.h"
#include "InteractionComponent.h"
#include "StatsComponent.h"
#include "MeleeHitComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Engine/Engine.h"
#include "GameFramework/DamageType.h"
#include "PlayerStatsOverlay.h"
#include "Engine/GameViewportClient.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "Bonfire.h"
#include "SoulDrop.h"
#include "LevelUpMenuWidget.h"
#include "EnemyCharacter.h"

namespace
{
	// turn the character toward the held movement input (relative to the camera); keeps the current facing if nothing is held
	void FaceHeldInputDirection(ACharacter* Character, const FVector2D& MoveInput)
	{
		AController* Controller = Character ? Character->GetController() : nullptr;
		if (!Controller || MoveInput.IsNearlyZero())
		{
			return;
		}

		const FRotationMatrix YawMatrix(FRotator(0.f, Controller->GetControlRotation().Yaw, 0.f));
		FVector Dir = YawMatrix.GetUnitAxis(EAxis::X) * MoveInput.Y + YawMatrix.GetUnitAxis(EAxis::Y) * MoveInput.X;
		Dir.Z = 0.f;
		if (Dir.Normalize())
		{
			Character->SetActorRotation(Dir.Rotation());
		}
	}
}

AOss_TermProjectCharacter::AOss_TermProjectCharacter()
{
	// Set size for collision capsule
	GetCapsuleComponent()->InitCapsuleSize(42.f, 96.0f);
		
	// Don't rotate when the controller rotates. Let that just affect the camera.
	bUseControllerRotationPitch = false;
	bUseControllerRotationYaw = false;
	bUseControllerRotationRoll = false;

	// Configure character movement
	// Free camera: the character turns toward the direction it moves in; rotating the camera doesn't turn the character
	GetCharacterMovement()->bOrientRotationToMovement = true;
	GetCharacterMovement()->bUseControllerDesiredRotation = false;
	GetCharacterMovement()->RotationRate = FRotator(0.0f, 500.0f, 0.0f);

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

	// Lock-on marker: small sphere placed in world space on the target's surface facing the camera
	LockOnMarker = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("LockOnMarker"));
	LockOnMarker->SetupAttachment(RootComponent);
	LockOnMarker->SetUsingAbsoluteLocation(true);
	LockOnMarker->SetUsingAbsoluteRotation(true);
	LockOnMarker->SetUsingAbsoluteScale(true);
	LockOnMarker->SetWorldScale3D(FVector(0.08f));
	LockOnMarker->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	LockOnMarker->SetGenerateOverlapEvents(false);
	LockOnMarker->SetCastShadow(false);
	LockOnMarker->SetHiddenInGame(true);
	static ConstructorHelpers::FObjectFinder<UStaticMesh> SphereMesh(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
	if (SphereMesh.Succeeded())
	{
		LockOnMarker->SetStaticMesh(SphereMesh.Object);
	}

	// Interaction (E)
	Interaction = CreateDefaultSubobject<UInteractionComponent>(TEXT("Interaction"));

	// Health / stamina
	Stats = CreateDefaultSubobject<UStatsComponent>(TEXT("Stats"));

	// Attack hit detection
	MeleeHit = CreateDefaultSubobject<UMeleeHitComponent>(TEXT("MeleeHit"));

	// Potion bottle: engine cylinder scaled down, placed in the right hand on BeginPlay, hidden until drinking
	PotionMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("PotionMesh"));
	PotionMesh->SetupAttachment(GetMesh());
	PotionMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	PotionMesh->SetGenerateOverlapEvents(false);
	PotionMesh->SetHiddenInGame(true);
	if (CylinderMesh.Succeeded())
	{
		PotionMesh->SetStaticMesh(CylinderMesh.Object);
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
	GetCharacterMovement()->MaxWalkSpeed = WalkSpeed;

	Stats->OnDeath.AddDynamic(this, &AOss_TermProjectCharacter::HandleDeath);

	// remembered for respawning
	StartTransform = GetActorTransform();
	MeshRelativeTransform = GetMesh()->GetRelativeTransform();
	MeshCollisionProfile = GetMesh()->GetCollisionProfileName();
	CapsuleCollision = GetCapsuleComponent()->GetCollisionEnabled();

	// level 1 values (leveling adds on top)
	BaseMaxHealth = Stats->GetMaxHealth();
	BaseMaxStamina = Stats->GetMaxStamina();

	// potion bottle in the right fist: upright along the knuckle line, like the stick grip
	PotionCharges = MaxPotionCharges;
	if (USkeletalMesh* SkelMesh = GetMesh()->GetSkeletalMeshAsset())
	{
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

		if (RefSkel.FindBoneIndex(TEXT("hand_r")) != INDEX_NONE && RefSkel.FindBoneIndex(TEXT("index_01_r")) != INDEX_NONE)
		{
			const FTransform Hand = RefComponentSpace(TEXT("hand_r"));
			const FVector Axis = (RefComponentSpace(TEXT("index_01_r")).GetLocation() - RefComponentSpace(TEXT("pinky_01_r")).GetLocation()).GetSafeNormal();
			const FVector Grip = FMath::Lerp(Hand.GetLocation(), RefComponentSpace(TEXT("middle_01_r")).GetLocation(), 0.6f);

			// 6cm wide, 14cm tall bottle, sticking out 5cm more on the thumb side
			const FTransform Bottle(FRotationMatrix::MakeFromZ(Axis).ToQuat(), Grip + Axis * 5.f, FVector(0.06f, 0.06f, 0.14f));
			PotionMesh->AttachToComponent(GetMesh(), FAttachmentTransformRules::SnapToTargetNotIncludingScale, TEXT("hand_r"));
			PotionMesh->SetRelativeTransform(Bottle.GetRelativeTransform(Hand));
		}
	}
	if (UMaterialInstanceDynamic* MID = PotionMesh->CreateDynamicMaterialInstance(0))
	{
		MID->SetVectorParameterValue(TEXT("Color"), PotionColor);
	}

	// lock-on marker color
	if (UMaterialInstanceDynamic* MID = LockOnMarker->CreateDynamicMaterialInstance(0))
	{
		MID->SetVectorParameterValue(TEXT("Color"), FLinearColor(1.f, 0.85f, 0.3f));
	}

	// roll speed curve: full speed, then ease out at the end
	RollStrengthCurve = NewObject<UCurveFloat>(this, TEXT("RollStrengthCurve"));
	RollStrengthCurve->FloatCurve.AddKey(0.0f, 1.0f);
	RollStrengthCurve->FloatCurve.AddKey(0.7f, 1.0f);
	RollStrengthCurve->FloatCurve.AddKey(1.0f, 0.2f);

	if (RollAnimation.IsNull() || !RollAnimation.LoadSynchronous())
	{
		UE_LOG(LogOss_TermProject, Warning, TEXT("'%s' Roll animation not found (%s). Rolling will move the character without an animation."), *GetNameSafe(this), *RollAnimation.ToString());
	}

	TArray<TSoftObjectPtr<UAnimSequenceBase>*> AttackAnims = { &LightAttackAnimation, &HeavyAttackAnimation, &StickHeavyAttackAnimation, &StickBlockAnimation, &PotionAnimation };
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
		if (!BlockAction)
		{
			BlockAction = MakeRuntimeAction(TEXT("IA_Block_Runtime"), EKeys::RightMouseButton);
		}
		if (!LockOnAction)
		{
			LockOnAction = MakeRuntimeAction(TEXT("IA_LockOn_Runtime"), EKeys::Q);
		}
		if (!InteractAction)
		{
			InteractAction = MakeRuntimeAction(TEXT("IA_Interact_Runtime"), EKeys::E);
		}
		if (!PotionAction)
		{
			PotionAction = MakeRuntimeAction(TEXT("IA_Potion_Runtime"), EKeys::R);
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

		// temporary health / stamina bars for the local player
		if (!StatsOverlay.IsValid())
		{
			if (APlayerController* PC = Cast<APlayerController>(GetController()))
			{
				ULocalPlayer* LocalPlayer = PC->GetLocalPlayer();
				if (LocalPlayer && LocalPlayer->ViewportClient)
				{
					TWeakObjectPtr<AOss_TermProjectCharacter> WeakThis(this);
					StatsOverlay = PlayerStatsOverlay::Create(Stats, TAttribute<FText>::CreateLambda([WeakThis]()
					{
						return WeakThis.IsValid() ? FText::FromString(FString::Printf(TEXT("Potion x%d  [R]"), WeakThis->GetPotionCharges())) : FText::GetEmpty();
					}), TAttribute<FText>::CreateLambda([WeakThis]()
					{
						return WeakThis.IsValid() ? FText::FromString(FString::Printf(TEXT("Souls  %d"), WeakThis->GetSouls())) : FText::GetEmpty();
					}));
					LocalPlayer->ViewportClient->AddViewportWidgetContent(StatsOverlay.ToSharedRef(), 10);
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

		// Blocking (held)
		EnhancedInputComponent->BindAction(BlockAction, ETriggerEvent::Started, this, &AOss_TermProjectCharacter::DoBlockStart);
		EnhancedInputComponent->BindAction(BlockAction, ETriggerEvent::Completed, this, &AOss_TermProjectCharacter::DoBlockEnd);
		EnhancedInputComponent->BindAction(BlockAction, ETriggerEvent::Canceled, this, &AOss_TermProjectCharacter::DoBlockEnd);

		// Lock-on
		EnhancedInputComponent->BindAction(LockOnAction, ETriggerEvent::Started, this, &AOss_TermProjectCharacter::ToggleLockOn);

		// Interacting
		EnhancedInputComponent->BindAction(InteractAction, ETriggerEvent::Started, this, &AOss_TermProjectCharacter::DoInteract);

		// Drinking a potion
		EnhancedInputComponent->BindAction(PotionAction, ETriggerEvent::Started, this, &AOss_TermProjectCharacter::DoDrinkPotion);
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
	// no moving while resting at a bonfire (only E gets up) or in the level-up menu
	if (bIsResting || bInLevelUpMenu)
	{
		return;
	}

	// remember the held direction so a roll can use it
	CachedMoveInput = FVector2D(Right, Forward);

	// no steering while rolling, attacking or blocking
	if (bIsRolling || bIsAttacking || bIsBlocking || bIsStaggered)
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
	// the mouse is for the menu
	if (bInLevelUpMenu)
	{
		return;
	}

	// the camera follows the target while locked on; a quick sideways flick switches to the next target on that side
	if (LockOnTarget)
	{
		LockOnSwitchInput += Yaw;
		const float Now = GetWorld()->GetTimeSeconds();
		if (FMath::Abs(LockOnSwitchInput) >= LockOnSwitchThreshold && Now - LastLockOnSwitchTime >= LockOnSwitchCooldown)
		{
			SwitchLockOnTarget(LockOnSwitchInput);
			LockOnSwitchInput = 0.f;
			LastLockOnSwitchTime = Now;
		}
		return;
	}

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
	if (bIsResting || bInLevelUpMenu || bIsRolling || bIsAttacking || bIsBlocking || bIsStaggered || bIsDrinking || !Movement->IsMovingOnGround() || !Stats->ConsumeStamina(RollStaminaCost))
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
	RollStartTime = GetWorld()->GetTimeSeconds();

	// face the roll direction instantly and don't turn until the roll ends
	SetActorRotation(RollDir.Rotation());
	UpdateRotationMode();

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
	UpdateRotationMode();
}

void AOss_TermProjectCharacter::AttackPressed(const FInputActionValue& Value)
{
	if (bIsResting || bInLevelUpMenu)
	{
		return;
	}

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

	PlayAttack(LightAttackAnimation, LightAttackStaminaCost, UnarmedLightDamage, UnarmedLightHitWindow, false);
}

void AOss_TermProjectCharacter::StickAttack()
{
	if (bIsRolling || bIsBlocking || bIsStaggered || bIsDrinking || !GetCharacterMovement()->IsMovingOnGround())
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
	if (!Anim || !AnimInstance || !Stats->HasStamina())
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

	Stats->ConsumeStamina(LightAttackStaminaCost);
	ScheduleHitWindow(StickSlashHitWindow, Length, StartTime, PlayRate, StickLightDamage, true);

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

	// the first slash faces the target / held movement direction (or keeps the current facing); chained slashes keep that facing
	if (!bChained)
	{
		FaceActionDirection();
	}
	UpdateRotationMode();
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
		if (PlayAttack(StickHeavyAttackAnimation, HeavyAttackStaminaCost, StickHeavyDamage, StickHeavyHitWindow, true, StickHeavyPlayRate * StickHeavySpeedMultiplier, StickHeavyRootMotionScale))
		{
			// a heavy attack ends the slash combo
			NextStickComboIndex = 0;
			LastStickAttackEndTime = -1000.f;
		}
		return;
	}

	PlayAttack(HeavyAttackAnimation, HeavyAttackStaminaCost, UnarmedHeavyDamage, UnarmedHeavyHitWindow, false);
}

void AOss_TermProjectCharacter::ScheduleHitWindow(FVector2D Window, float AnimLength, float StartTime, float PlayRate, float Damage, bool bStick)
{
	CancelHitWindow();

	// Strength
	Damage *= GetDamageMultiplier();

	TArray<FMeleeHitShape> Shapes;
	if (bStick)
	{
		// the whole stick: engine cylinder is 100cm long along Z, the component's scale stretches it to StickLength
		FMeleeHitShape Shape;
		Shape.Component = StickMesh;
		Shape.Start = FVector(0.f, 0.f, -50.f);
		Shape.End = FVector(0.f, 0.f, 50.f);
		Shape.Radius = StickHitRadius;
		Shapes.Add(Shape);
	}
	else
	{
		for (const TCHAR* Bone : { TEXT("hand_r"), TEXT("hand_l") })
		{
			FMeleeHitShape Shape;
			Shape.Component = GetMesh();
			Shape.Socket = Bone;
			Shape.Radius = FistHitRadius;
			Shapes.Add(Shape);
		}
	}

	// animation time -> real time
	PlayRate = FMath::Max(PlayRate, 0.05f);
	const float OpenDelay = (Window.X * AnimLength - StartTime) / PlayRate;
	const float CloseDelay = (Window.Y * AnimLength - StartTime) / PlayRate;
	if (CloseDelay <= 0.f)
	{
		return;
	}

	auto Open = [this, Shapes, Damage]() { MeleeHit->BeginHitWindow(Shapes, Damage); };
	if (OpenDelay <= 0.f)
	{
		Open();
	}
	else
	{
		GetWorldTimerManager().SetTimer(HitWindowStartTimer, FTimerDelegate::CreateWeakLambda(this, Open), OpenDelay, false);
	}
	GetWorldTimerManager().SetTimer(HitWindowEndTimer, FTimerDelegate::CreateWeakLambda(this, [this]() { MeleeHit->EndHitWindow(); }), CloseDelay, false);
}

void AOss_TermProjectCharacter::CancelHitWindow()
{
	GetWorldTimerManager().ClearTimer(HitWindowStartTimer);
	GetWorldTimerManager().ClearTimer(HitWindowEndTimer);
	MeleeHit->EndHitWindow();
}

bool AOss_TermProjectCharacter::PlayAttack(const TSoftObjectPtr<UAnimSequenceBase>& Animation, float StaminaCost, float Damage, FVector2D HitWindow, bool bStick, float PlayRate, float RootMotionScale)
{
	PlayRate = FMath::Max(PlayRate, 0.05f);
	if (bIsAttacking || bIsRolling || bIsBlocking || bIsStaggered || bIsDrinking || !GetCharacterMovement()->IsMovingOnGround() || !Stats->HasStamina())
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

	Stats->ConsumeStamina(StaminaCost);
	ScheduleHitWindow(HitWindow, Anim->GetPlayLength(), 0.f, PlayRate, Damage, bStick);

	bIsAttacking = true;
	bIsStickAttack = false;
	SetAnimRootMotionTranslationScale(RootMotionScale);

	// attack toward the target / held movement direction (or the current facing), then keep that facing until the attack ends
	FaceActionDirection();
	UpdateRotationMode();
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

	CancelHitWindow();
	bIsAttacking = false;
	bIsStickAttack = false;
	bStickComboQueued = false;

	// resume normal turning
	UpdateRotationMode();

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
	// no weapon swaps while drinking, staggered or resting
	if (bIsDrinking || bIsStaggered || bIsResting || bInLevelUpMenu)
	{
		return;
	}

	if (bStickEquipped)
	{
		StopBlocking();
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

void AOss_TermProjectCharacter::DoInteract()
{
	// E again at the bonfire: stand up
	if (bIsResting)
	{
		StopResting();
		return;
	}

	// E in the level-up menu: close it
	if (bInLevelUpMenu)
	{
		CloseLevelUpMenu();
		return;
	}

	if (IsBusy() || bIsDrinking || !GetCharacterMovement()->IsMovingOnGround())
	{
		return;
	}

	Interaction->TryInteract();
}

void AOss_TermProjectCharacter::DoDrinkPotion()
{
	if (bIsDrinking || IsBusy() || PotionCharges <= 0 || Stats->IsDead() || !GetCharacterMovement()->IsMovingOnGround())
	{
		return;
	}

	// upper-body animation: the legs keep walking (needs the PotionSlotName slot behind a Layered blend per bone in the anim blueprint)
	float Duration = FallbackPotionDuration;
	const float BlendOut = 0.2f;
	UAnimSequenceBase* Anim = PotionAnimation.Get();
	UAnimInstance* AnimInstance = GetMesh() ? GetMesh()->GetAnimInstance() : nullptr;
	if (Anim && AnimInstance && AnimInstance->PlaySlotAnimationAsDynamicMontage(Anim, PotionSlotName, 0.15f, BlendOut))
	{
		Duration = Anim->GetPlayLength();
	}

	--PotionCharges;
	bIsDrinking = true;

	// weapon away, bottle in hand
	StickMesh->SetHiddenInGame(true);
	PotionMesh->SetHiddenInGame(false);
	UpdateRotationMode();

	GetWorldTimerManager().SetTimer(PotionHealTimer, this, &AOss_TermProjectCharacter::ApplyPotionHeal, FMath::Max(Duration * PotionHealFraction, 0.05f), false);
	GetWorldTimerManager().SetTimer(PotionEndTimer, this, &AOss_TermProjectCharacter::EndDrinkPotion, FMath::Max(Duration - BlendOut, 0.1f), false);
}

void AOss_TermProjectCharacter::ApplyPotionHeal()
{
	Stats->Heal(PotionHealAmount);
}

void AOss_TermProjectCharacter::EndDrinkPotion()
{
	bIsDrinking = false;
	PotionMesh->SetHiddenInGame(true);
	StickMesh->SetHiddenInGame(!bStickEquipped);
	UpdateRotationMode();
}

void AOss_TermProjectCharacter::DoBlockStart()
{
	bBlockHeld = true;

	UCharacterMovementComponent* Movement = GetCharacterMovement();
	if (!bStickEquipped || bIsResting || bInLevelUpMenu || bIsBlocking || bIsRolling || bIsAttacking || bIsStaggered || bIsDrinking || !Movement->IsMovingOnGround())
	{
		return;
	}

	UAnimSequenceBase* Anim = StickBlockAnimation.Get();
	UAnimInstance* AnimInstance = GetMesh() ? GetMesh()->GetAnimInstance() : nullptr;
	if (!Anim || !AnimInstance)
	{
		return;
	}

	// the animation is a held pose: the blend-in raises the stick, looping keeps it up while the button is held
	if (!AnimInstance->PlaySlotAnimationAsDynamicMontage(Anim, AttackSlotName, BlockRaiseTime, BlockLowerTime, 1.f, 100000))
	{
		return;
	}

	bIsBlocking = true;
	BlockStartTime = GetWorld()->GetTimeSeconds();

	// block toward the target / held movement direction (or the current facing) and stand still while blocking
	FaceActionDirection();
	UpdateRotationMode();
	Movement->StopMovementImmediately();
}

void AOss_TermProjectCharacter::DoBlockEnd()
{
	bBlockHeld = false;

	// frozen after a block: the guard stays up until the stagger ends
	if (!bIsStaggered)
	{
		StopBlocking();
	}
}

void AOss_TermProjectCharacter::StopBlocking()
{
	if (!bIsBlocking)
	{
		return;
	}

	bIsBlocking = false;

	if (UAnimInstance* AnimInstance = GetMesh() ? GetMesh()->GetAnimInstance() : nullptr)
	{
		AnimInstance->StopSlotAnimation(BlockLowerTime, AttackSlotName);
	}

	UpdateRotationMode();
}

void AOss_TermProjectCharacter::DoSprintStart()
{
	bIsSprinting = true;
	bSprintExhausted = false;
	UpdateRotationMode();
}

void AOss_TermProjectCharacter::DoSprintEnd()
{
	bIsSprinting = false;
	bSprintExhausted = false;
	UpdateRotationMode();
}

bool AOss_TermProjectCharacter::IsSprintActive() const
{
	return bIsSprinting && !bSprintExhausted && !bIsDrinking && Stats->HasStamina();
}

float AOss_TermProjectCharacter::TakeDamage(float DamageAmount, FDamageEvent const& DamageEvent, AController* EventInstigator, AActor* DamageCauser)
{
	const float Damage = Super::TakeDamage(DamageAmount, DamageEvent, EventInstigator, DamageCauser);
	if (Damage <= 0.f || Stats->IsDead() || bIsResting)
	{
		return 0.f;
	}

	// rolling through the hit
	if (IsInvincible())
	{
		ShowCombatText(TEXT("DODGE"), FColor::Cyan);
		return 0.f;
	}

	// guarding against a hit from the front
	if (bIsBlocking && IsInFront(DamageCauser))
	{
		// guard raised just before the hit: nothing lost, no stagger
		if (GetWorld()->GetTimeSeconds() - BlockStartTime <= PerfectBlockWindow)
		{
			ShowCombatText(TEXT("PERFECT BLOCK"), FColor::Yellow);
			return 0.f;
		}

		// normal block: stamina instead of health, then a short freeze. Not enough stamina: the guard breaks
		const float StaminaCost = Damage * BlockStaminaPerDamage;
		const bool bGuardBreak = Stats->GetStamina() < StaminaCost;
		Stats->ConsumeStamina(StaminaCost);

		if (bGuardBreak)
		{
			ShowCombatText(TEXT("GUARD BREAK"), FColor::Red);
			bBlockHeld = false;
			StopBlocking();
			StartStagger(GuardBreakStaggerTime);
		}
		else
		{
			ShowCombatText(TEXT("BLOCK"), FColor::White);
			StartStagger(BlockStaggerTime);
		}
		return 0.f;
	}

	const float Taken = Stats->ApplyDamage(Damage, DamageCauser);
	if (Taken > 0.f && !Stats->IsDead())
	{
		PlayHitReaction(DamageCauser);
	}
	return Taken;
}

void AOss_TermProjectCharacter::CancelAllActions()
{
	FTimerManager& Timers = GetWorldTimerManager();

	// a hit (or death) closes the level-up menu
	CloseLevelUpMenu();

	// roll (and its push)
	Timers.ClearTimer(RollEndTimer);
	if (bIsRolling)
	{
		GetCharacterMovement()->RemoveRootMotionSourceByID(RollRootMotionID);
		bIsRolling = false;
	}

	// attack / combo
	Timers.ClearTimer(AttackEndTimer);
	Timers.ClearTimer(StickComboChainTimer);
	CancelHitWindow();
	if (bIsAttacking)
	{
		bIsAttacking = false;
		bIsStickAttack = false;
		bStickComboQueued = false;
		NextStickComboIndex = 0;
		LastStickAttackEndTime = -1000.f;
		SetAnimRootMotionTranslationScale(1.f);
		EndAttackCamera();
	}

	// guard (the button has to be pressed again)
	StopBlocking();

	// potion: interrupted before the heal = the charge is lost
	Timers.ClearTimer(PotionHealTimer);
	Timers.ClearTimer(PotionEndTimer);
	if (bIsDrinking)
	{
		EndDrinkPotion();
	}

	if (UAnimInstance* AnimInstance = GetMesh() ? GetMesh()->GetAnimInstance() : nullptr)
	{
		AnimInstance->StopAllMontages(0.1f);
	}
}

void AOss_TermProjectCharacter::PlayHitReaction(AActor* DamageCauser)
{
	CancelAllActions();

	// turn toward the attacker (the flinch animation is a hit from the front)
	if (DamageCauser)
	{
		FVector Dir = DamageCauser->GetActorLocation() - GetActorLocation();
		Dir.Z = 0.f;
		if (!Dir.IsNearlyZero())
		{
			SetActorRotation(Dir.Rotation());
		}
	}

	if (UAnimSequenceBase* Anim = HitReactAnimation.LoadSynchronous())
	{
		if (UAnimInstance* AnimInstance = GetMesh() ? GetMesh()->GetAnimInstance() : nullptr)
		{
			AnimInstance->PlaySlotAnimationAsDynamicMontage(Anim, AttackSlotName, 0.05f, 0.2f);
		}
	}

	StartStagger(HitStaggerTime);
}

bool AOss_TermProjectCharacter::IsInvincible() const
{
	if (!bIsRolling)
	{
		return false;
	}

	const float T = GetWorld()->GetTimeSeconds() - RollStartTime;
	return T >= RollInvincibleStart && T <= RollInvincibleStart + RollInvincibleDuration;
}

bool AOss_TermProjectCharacter::IsInFront(const AActor* DamageCauser) const
{
	if (!DamageCauser)
	{
		return true;
	}

	FVector ToCauser = DamageCauser->GetActorLocation() - GetActorLocation();
	ToCauser.Z = 0.f;
	if (!ToCauser.Normalize())
	{
		return true;
	}

	return FVector::DotProduct(GetActorForwardVector(), ToCauser) >= FMath::Cos(FMath::DegreesToRadians(BlockAngle));
}

void AOss_TermProjectCharacter::StartStagger(float Duration)
{
	bIsStaggered = true;
	GetCharacterMovement()->StopMovementImmediately();
	UpdateRotationMode();
	GetWorldTimerManager().SetTimer(StaggerTimer, this, &AOss_TermProjectCharacter::EndStagger, FMath::Max(Duration, 0.01f), false);
}

void AOss_TermProjectCharacter::EndStagger()
{
	bIsStaggered = false;

	// the block button was released while frozen
	if (bIsBlocking && !bBlockHeld)
	{
		StopBlocking();
	}

	UpdateRotationMode();
}

void AOss_TermProjectCharacter::ShowCombatText(const FString& Text, const FColor& Color) const
{
	if (bShowCombatDebugText && GEngine)
	{
		GEngine->AddOnScreenDebugMessage(-1, 1.2f, Color, Text, true, FVector2D(2.f, 2.f));
	}
	UE_LOG(LogOss_TermProject, Log, TEXT("'%s' %s"), *GetNameSafe(this), *Text);
}

void AOss_TermProjectCharacter::HandleDeath(AActor* DamageCauser)
{
	// stop everything
	CloseLevelUpMenu();
	GetWorldTimerManager().ClearTimer(StaggerTimer);
	bIsStaggered = false;
	bBlockHeld = false;
	StopBlocking();
	ClearLockOn();
	GetWorldTimerManager().ClearTimer(RollEndTimer);
	GetWorldTimerManager().ClearTimer(AttackEndTimer);
	GetWorldTimerManager().ClearTimer(StickComboChainTimer);
	CancelHitWindow();
	GetWorldTimerManager().ClearTimer(PotionHealTimer);
	GetWorldTimerManager().ClearTimer(PotionEndTimer);
	bIsRolling = bIsAttacking = bIsSprinting = bIsDrinking = false;
	Interaction->SetInteractionEnabled(false);

	if (APlayerController* PC = Cast<APlayerController>(GetController()))
	{
		DisableInput(PC);
	}

	// collapse as a ragdoll
	GetCharacterMovement()->DisableMovement();
	GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	GetMesh()->SetCollisionProfileName(TEXT("Ragdoll"));
	GetMesh()->SetSimulatePhysics(true);

	if (GEngine)
	{
		GEngine->AddOnScreenDebugMessage(-1, RespawnDelay, FColor::Red, TEXT("YOU DIED"), true, FVector2D(4.f, 4.f));
	}

	// souls stay where we fell; souls still lying there from the previous death are lost
	if (DroppedSouls)
	{
		DroppedSouls->Destroy();
		DroppedSouls = nullptr;
	}
	if (Souls > 0)
	{
		DroppedSouls = ASoulDrop::SpawnAt(this, GetActorLocation(), Souls);
		Souls = 0;
	}

	// back at the last bonfire after a moment
	GetWorldTimerManager().SetTimer(RespawnTimer, this, &AOss_TermProjectCharacter::Respawn, FMath::Max(RespawnDelay, 0.1f), false);

	UE_LOG(LogOss_TermProject, Log, TEXT("'%s' died (killed by %s)"), *GetNameSafe(this), *GetNameSafe(DamageCauser));
}

void AOss_TermProjectCharacter::Respawn()
{
	// move to the bonfire (or where the level started) FIRST, while collision is still off:
	// turning collision back on at the death spot would instantly pick up the souls dropped there
	const FTransform Target = LastBonfire ? LastBonfire->GetRespawnTransform() : StartTransform;
	const FRotator Facing(0.f, Target.Rotator().Yaw, 0.f);
	TeleportTo(Target.GetLocation(), Facing);

	// alive before collision comes back, so souls dropped right next to the respawn spot still count
	Stats->RestoreAll();

	// un-ragdoll: physics off, mesh back under the capsule
	USkeletalMeshComponent* SkelMesh = GetMesh();
	SkelMesh->SetSimulatePhysics(false);
	SkelMesh->SetAllBodiesSimulatePhysics(false);
	SkelMesh->AttachToComponent(GetCapsuleComponent(), FAttachmentTransformRules::KeepRelativeTransform);
	SkelMesh->SetRelativeTransform(MeshRelativeTransform);
	SkelMesh->SetCollisionProfileName(MeshCollisionProfile);
	if (UAnimInstance* AnimInstance = SkelMesh->GetAnimInstance())
	{
		AnimInstance->StopAllMontages(0.f);
	}
	GetCapsuleComponent()->SetCollisionEnabled(CapsuleCollision);

	if (AController* PC = GetController())
	{
		PC->SetControlRotation(Facing);
	}

	UCharacterMovementComponent* Movement = GetCharacterMovement();
	Movement->StopMovementImmediately();
	Movement->SetMovementMode(MOVE_Walking);

	// fresh state
	Stats->RestoreAll();
	RefillPotions();
	GetWorldTimerManager().ClearTimer(RestAnimTimer);
	bIsResting = false;
	bIsStandingUp = false;
	bSprintExhausted = false;
	CachedMoveInput = FVector2D::ZeroVector;
	PotionMesh->SetHiddenInGame(true);
	StickMesh->SetHiddenInGame(!bStickEquipped);
	ResetAttackCamera();
	UpdateRotationMode();

	Interaction->SetInteractionEnabled(true);
	if (APlayerController* PC = Cast<APlayerController>(GetController()))
	{
		EnableInput(PC);
	}

	// the world comes back too
	AEnemyCharacter::ResetAllEnemies(this);

	UE_LOG(LogOss_TermProject, Log, TEXT("'%s' respawned at %s"), *GetNameSafe(this), LastBonfire ? *GetNameSafe(LastBonfire) : TEXT("the start"));
}

void AOss_TermProjectCharacter::AddSouls(int32 Amount)
{
	Souls = FMath::Max(Souls + Amount, 0);
}

int32 AOss_TermProjectCharacter::GetStatLevel(ELevelStat Stat) const
{
	switch (Stat)
	{
	case ELevelStat::Vigor:		return VigorLevel;
	case ELevelStat::Endurance:	return EnduranceLevel;
	case ELevelStat::Strength:	return StrengthLevel;
	default:					return 1;
	}
}

bool AOss_TermProjectCharacter::LevelUp(ELevelStat Stat)
{
	const int32 Cost = GetLevelUpCost();
	if (Souls < Cost || Stats->IsDead())
	{
		return false;
	}

	Souls -= Cost;
	switch (Stat)
	{
	case ELevelStat::Vigor:
		++VigorLevel;
		Stats->SetMaxHealth(BaseMaxHealth + (VigorLevel - 1) * HealthPerVigor);
		break;
	case ELevelStat::Endurance:
		++EnduranceLevel;
		Stats->SetMaxStamina(BaseMaxStamina + (EnduranceLevel - 1) * StaminaPerEndurance);
		break;
	case ELevelStat::Strength:
		++StrengthLevel;
		break;
	}

	UE_LOG(LogOss_TermProject, Log, TEXT("'%s' leveled up to %d (cost %d souls)"), *GetNameSafe(this), GetPlayerLevel(), Cost);
	return true;
}

void AOss_TermProjectCharacter::OpenLevelUpMenu(AActor* Npc)
{
	APlayerController* PC = Cast<APlayerController>(GetController());
	ULocalPlayer* LocalPlayer = PC ? PC->GetLocalPlayer() : nullptr;
	if (bInLevelUpMenu || Stats->IsDead() || !LocalPlayer || !LocalPlayer->ViewportClient)
	{
		return;
	}

	// stop and face the NPC
	bIsSprinting = false;
	CachedMoveInput = FVector2D::ZeroVector;
	GetCharacterMovement()->StopMovementImmediately();
	if (Npc)
	{
		FVector ToNpc = Npc->GetActorLocation() - GetActorLocation();
		ToNpc.Z = 0.f;
		if (!ToNpc.IsNearlyZero())
		{
			SetActorRotation(ToNpc.Rotation());
		}
	}
	bInLevelUpMenu = true;
	UpdateRotationMode();

	LevelUpMenu = LevelUpMenuWidget::Create(this);
	LocalPlayer->ViewportClient->AddViewportWidgetContent(LevelUpMenu.ToSharedRef(), 20);

	// mouse cursor for the buttons; keys still reach the game (E closes)
	PC->SetShowMouseCursor(true);
	FInputModeGameAndUI InputMode;
	InputMode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
	InputMode.SetHideCursorDuringCapture(false);
	PC->SetInputMode(InputMode);
}

void AOss_TermProjectCharacter::CloseLevelUpMenu()
{
	if (!bInLevelUpMenu)
	{
		return;
	}
	bInLevelUpMenu = false;

	if (LevelUpMenu.IsValid())
	{
		if (UGameViewportClient* Viewport = GetWorld() ? GetWorld()->GetGameViewport() : nullptr)
		{
			Viewport->RemoveViewportWidgetContent(LevelUpMenu.ToSharedRef());
		}
		LevelUpMenu.Reset();
	}

	if (APlayerController* PC = Cast<APlayerController>(GetController()))
	{
		PC->SetShowMouseCursor(false);
		PC->SetInputMode(FInputModeGameOnly());
	}
	UpdateRotationMode();
}

void AOss_TermProjectCharacter::StartResting(ABonfire* Bonfire)
{
	if (bIsResting || Stats->IsDead() || !Bonfire)
	{
		return;
	}

	// drop whatever was going on
	StopBlocking();
	ClearLockOn();
	bIsSprinting = false;
	CachedMoveInput = FVector2D::ZeroVector;
	GetCharacterMovement()->StopMovementImmediately();

	bIsResting = true;
	bIsStandingUp = false;
	LastBonfire = Bonfire;

	// face the fire
	FVector ToFire = Bonfire->GetActorLocation() - GetActorLocation();
	ToFire.Z = 0.f;
	if (!ToFire.IsNearlyZero())
	{
		SetActorRotation(ToFire.Rotation());
	}
	UpdateRotationMode();

	// weapon away, kneel down, then hold the kneeling pose
	StickMesh->SetHiddenInGame(true);
	PotionMesh->SetHiddenInGame(true);
	const float DownLength = PlayRestAnimation(RestDownAnimation, 0.2f, 0.f);
	if (DownLength > 0.f)
	{
		GetWorldTimerManager().SetTimer(RestAnimTimer, this, &AOss_TermProjectCharacter::PlayRestIdle, FMath::Max(DownLength - 0.05f, 0.05f), false);
	}
	else
	{
		PlayRestIdle();
	}

	// soulslike rest: full health, stamina and potions, and the enemies come back
	Stats->RestoreAll();
	RefillPotions();
	AEnemyCharacter::ResetAllEnemies(this);
}

void AOss_TermProjectCharacter::StopResting()
{
	if (!bIsResting || bIsStandingUp)
	{
		return;
	}

	// get up; still resting (can't act, not attacked) until the animation ends
	bIsStandingUp = true;
	const float UpLength = PlayRestAnimation(RestUpAnimation, 0.1f, 0.25f);
	if (UpLength > 0.f)
	{
		GetWorldTimerManager().SetTimer(RestAnimTimer, this, &AOss_TermProjectCharacter::FinishStandingUp, FMath::Max(UpLength - 0.25f, 0.05f), false);
	}
	else
	{
		if (UAnimInstance* AnimInstance = GetMesh() ? GetMesh()->GetAnimInstance() : nullptr)
		{
			AnimInstance->StopSlotAnimation(0.3f, RestSlotName);
		}
		FinishStandingUp();
	}
}

float AOss_TermProjectCharacter::PlayRestAnimation(const TSoftObjectPtr<UAnimSequenceBase>& Animation, float BlendIn, float BlendOut, int32 LoopCount)
{
	UAnimSequenceBase* Anim = Animation.LoadSynchronous();
	UAnimInstance* AnimInstance = GetMesh() ? GetMesh()->GetAnimInstance() : nullptr;
	if (!Anim || !AnimInstance || !AnimInstance->PlaySlotAnimationAsDynamicMontage(Anim, RestSlotName, BlendIn, BlendOut, 1.f, LoopCount))
	{
		return 0.f;
	}
	return Anim->GetPlayLength();
}

void AOss_TermProjectCharacter::PlayRestIdle()
{
	if (bIsResting && !bIsStandingUp)
	{
		PlayRestAnimation(RestIdleAnimation, 0.1f, 0.2f, 100000);
	}
}

void AOss_TermProjectCharacter::FinishStandingUp()
{
	GetWorldTimerManager().ClearTimer(RestAnimTimer);
	bIsResting = false;
	bIsStandingUp = false;
	StickMesh->SetHiddenInGame(!bStickEquipped);
	UpdateRotationMode();
}

void AOss_TermProjectCharacter::DebugDamage(float Amount)
{
	UGameplayStatics::ApplyDamage(this, Amount, GetController(), nullptr, UDamageType::StaticClass());
}

void AOss_TermProjectCharacter::DebugRestore()
{
	Stats->RestoreAll();
	RefillPotions();
}

void AOss_TermProjectCharacter::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	CloseLevelUpMenu();

	if (StatsOverlay.IsValid())
	{
		if (UGameViewportClient* Viewport = GetWorld() ? GetWorld()->GetGameViewport() : nullptr)
		{
			Viewport->RemoveViewportWidgetContent(StatsOverlay.ToSharedRef());
		}
		StatsOverlay.Reset();
	}

	Super::EndPlay(EndPlayReason);
}

void AOss_TermProjectCharacter::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	// running uses stamina; running out drops to walking until the sprint key is pressed again
	UCharacterMovementComponent* Movement = GetCharacterMovement();
	const bool bWasSprintActive = IsSprintActive();
	if (bWasSprintActive && Movement->IsMovingOnGround() && Movement->Velocity.Size2D() > 10.f && !IsBusy())
	{
		Stats->DrainStamina(SprintStaminaPerSecond, DeltaSeconds);
		if (!Stats->HasStamina())
		{
			bSprintExhausted = true;
		}
	}
	Movement->MaxWalkSpeed = bIsDrinking ? PotionWalkSpeed : (IsSprintActive() ? SprintSpeed : WalkSpeed);
	if (bWasSprintActive != IsSprintActive())
	{
		UpdateRotationMode();
	}

	if (!LockOnTarget)
	{
		return;
	}

	// drop the lock if the target is gone or too far
	if (!IsValid(LockOnTarget) || LockOnTarget->IsHidden() || !LockOnTarget->ActorHasTag(LockOnTag) || FVector::Dist(GetActorLocation(), LockOnTarget->GetActorLocation()) > LockOnBreakDistance)
	{
		ClearLockOn();
		return;
	}

	// sideways input fades out quickly: slow mouse drift never adds up to a switch
	LockOnSwitchInput = FMath::FInterpTo(LockOnSwitchInput, 0.f, DeltaSeconds, 10.f);

	float TargetRadius = 0.f;
	const FVector TargetPoint = GetLockOnPoint(LockOnTarget, &TargetRadius);

	// camera: turn toward the target, looking a bit down so the character stays in view
	if (AController* PC = GetController())
	{
		const FVector ViewOrigin = GetActorLocation() + FVector(0.f, 0.f, BaseEyeHeight);
		FRotator Desired = (TargetPoint - ViewOrigin).Rotation();
		Desired.Pitch = FMath::Clamp(Desired.Pitch + LockOnPitchOffset, -60.f, 30.f);
		Desired.Roll = 0.f;
		PC->SetControlRotation(FMath::RInterpTo(PC->GetControlRotation(), Desired, DeltaSeconds, LockOnCameraSpeed));
	}

	// character: keep facing the target while walking or blocking (sprinting turns toward the movement direction; rolls and attacks keep their facing)
	if (!bIsRolling && !bIsAttacking && !IsSprintActive())
	{
		FVector ToTarget = TargetPoint - GetActorLocation();
		ToTarget.Z = 0.f;
		if (!ToTarget.IsNearlyZero())
		{
			SetActorRotation(FMath::RInterpTo(GetActorRotation(), ToTarget.Rotation(), DeltaSeconds, LockOnTurnSpeed));
		}
	}

	// marker on the target's surface, on the side facing the camera
	const FVector CameraLocation = FollowCamera->GetComponentLocation();
	LockOnMarker->SetWorldLocation(TargetPoint + (CameraLocation - TargetPoint).GetSafeNormal() * (TargetRadius + 5.f));
}

void AOss_TermProjectCharacter::ToggleLockOn()
{
	if (LockOnTarget)
	{
		ClearLockOn();
		return;
	}

	LockOnTarget = FindLockOnTarget();
	if (LockOnTarget)
	{
		LockOnSwitchInput = 0.f;
		LockOnMarker->SetHiddenInGame(false);
		UpdateRotationMode();
	}
}

bool AOss_TermProjectCharacter::IsValidLockOnCandidate(AActor* Candidate, float Range) const
{
	if (!IsValid(Candidate) || Candidate == this || !Candidate->ActorHasTag(LockOnTag) || Candidate->IsHidden())
	{
		return false;
	}

	const FVector Point = GetLockOnPoint(Candidate);
	if (FVector::Dist(GetActorLocation(), Point) > Range)
	{
		return false;
	}

	// must be visible from the camera
	FCollisionQueryParams Params(SCENE_QUERY_STAT(LockOnSight), false, this);
	FHitResult Hit;
	return !GetWorld()->LineTraceSingleByChannel(Hit, FollowCamera->GetComponentLocation(), Point, ECC_Visibility, Params) || Hit.GetActor() == Candidate;
}

void AOss_TermProjectCharacter::SwitchLockOnTarget(float Direction)
{
	if (!LockOnTarget || FMath::IsNearlyZero(Direction))
	{
		return;
	}

	const FVector ViewLocation = FollowCamera->GetComponentLocation();
	const FVector ViewForward = FollowCamera->GetForwardVector();
	const FVector ViewRight = FollowCamera->GetRightVector();

	// horizontal screen angle of a point relative to the view direction (negative = left, positive = right)
	auto ScreenAngle = [&](const FVector& Point)
	{
		const FVector ToPoint = Point - ViewLocation;
		return FMath::RadiansToDegrees(FMath::Atan2(FVector::DotProduct(ToPoint, ViewRight), FVector::DotProduct(ToPoint, ViewForward)));
	};

	const float CurrentAngle = ScreenAngle(GetLockOnPoint(LockOnTarget));
	const float Side = FMath::Sign(Direction);

	AActor* Best = nullptr;
	float BestDelta = TNumericLimits<float>::Max();

	for (TActorIterator<AActor> It(GetWorld()); It; ++It)
	{
		AActor* Candidate = *It;
		if (Candidate == LockOnTarget || !IsValidLockOnCandidate(Candidate, LockOnRange))
		{
			continue;
		}

		const FVector Point = GetLockOnPoint(Candidate);
		if (FVector::DotProduct(Point - ViewLocation, ViewForward) <= 0.f)
		{
			continue; // behind the camera
		}

		// the nearest target on the flicked side
		const float Delta = (ScreenAngle(Point) - CurrentAngle) * Side;
		if (Delta > 0.5f && Delta < BestDelta)
		{
			BestDelta = Delta;
			Best = Candidate;
		}
	}

	if (Best)
	{
		LockOnTarget = Best;
	}
}

void AOss_TermProjectCharacter::ClearLockOn()
{
	LockOnTarget = nullptr;
	LockOnMarker->SetHiddenInGame(true);
	UpdateRotationMode();
}

AActor* AOss_TermProjectCharacter::FindLockOnTarget() const
{
	const FVector ViewLocation = FollowCamera->GetComponentLocation();
	const FVector ViewDir = FollowCamera->GetForwardVector();
	const float MinDot = FMath::Cos(FMath::DegreesToRadians(LockOnMaxAngle));

	AActor* Best = nullptr;
	float BestScore = TNumericLimits<float>::Max();

	for (TActorIterator<AActor> It(GetWorld()); It; ++It)
	{
		AActor* Candidate = *It;
		if (!IsValidLockOnCandidate(Candidate, LockOnRange))
		{
			continue;
		}

		const FVector Point = GetLockOnPoint(Candidate);
		const FVector ToPoint = (Point - ViewLocation).GetSafeNormal();
		const float Dot = FVector::DotProduct(ViewDir, ToPoint);
		if (Dot < MinDot)
		{
			continue;
		}

		// prefer the target closest to the center of the view, then the closer one
		const float Score = (1.f - Dot) * 10000.f + FVector::Dist(GetActorLocation(), Point);
		if (Score < BestScore)
		{
			BestScore = Score;
			Best = Candidate;
		}
	}

	return Best;
}

FVector AOss_TermProjectCharacter::GetLockOnPoint(const AActor* Target, float* OutRadius) const
{
	FVector Origin, Extent;
	Target->GetActorBounds(true, Origin, Extent);
	if (OutRadius)
	{
		*OutRadius = FMath::Min3(Extent.X, Extent.Y, Extent.Z);
	}
	return Origin;
}

void AOss_TermProjectCharacter::UpdateRotationMode()
{
	UCharacterMovementComponent* Movement = GetCharacterMovement();
	Movement->bUseControllerDesiredRotation = false;

	// locked on (and not sprinting): Tick faces the target, so walking strafes around it
	Movement->bOrientRotationToMovement = !IsBusy() && !(LockOnTarget && !IsSprintActive());
}

void AOss_TermProjectCharacter::FaceActionDirection()
{
	if (LockOnTarget)
	{
		FVector ToTarget = GetLockOnPoint(LockOnTarget) - GetActorLocation();
		ToTarget.Z = 0.f;
		if (!ToTarget.IsNearlyZero())
		{
			SetActorRotation(ToTarget.Rotation());
			return;
		}
	}

	FaceHeldInputDirection(this, CachedMoveInput);
}
