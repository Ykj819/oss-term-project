// Bonfire (rest point): interact (E) to restore health, stamina and potions. Look: SM_Bonfire + flickering SM_BonfireFlame

#include "Bonfire.h"
#include "Oss_TermProjectCharacter.h"
#include "StatsComponent.h"
#include "Oss_TermProject.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"
#include "TimerManager.h"
#include "Engine/Engine.h"
#include "Kismet/GameplayStatics.h"
#include "EngineUtils.h"

ABonfire::ABonfire()
{
	PrimaryActorTick.bCanEverTick = false;

	// origin on the floor; the box sits on top of it
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));

	Body = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Body"));
	Body->SetupAttachment(RootComponent);
	Body->SetCollisionProfileName(UCollisionProfile::BlockAll_ProfileName);
	Body->SetCollisionResponseToChannel(ECC_Camera, ECR_Ignore);

	// pivots of both meshes = centre of the fire on the floor
	static ConstructorHelpers::FObjectFinder<UStaticMesh> BonfireMesh(TEXT("/Game/Environment/Props/SM_Bonfire.SM_Bonfire"));
	if (BonfireMesh.Succeeded())
	{
		Body->SetStaticMesh(BonfireMesh.Object);
	}

	Flame = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Flame"));
	Flame->SetupAttachment(RootComponent);
	Flame->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Flame->SetCastShadow(false);
	static ConstructorHelpers::FObjectFinder<UStaticMesh> FlameMesh(TEXT("/Game/Environment/Props/SM_BonfireFlame.SM_BonfireFlame"));
	if (FlameMesh.Succeeded())
	{
		Flame->SetStaticMesh(FlameMesh.Object);
	}

	Glow = CreateDefaultSubobject<UPointLightComponent>(TEXT("Glow"));
	Glow->SetupAttachment(RootComponent);
	Glow->SetAttenuationRadius(600.f);
	Glow->SetCastShadows(false);
}

void ABonfire::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);

	Body->SetRelativeScale3D(FVector::OneVector);
	Body->SetRelativeLocation(FVector::ZeroVector);
	Glow->SetRelativeLocation(FVector(0.f, 0.f, 70.f));		// middle of the flame
	Glow->SetLightColor(Color);
	Glow->SetIntensity(GlowIntensity);
}

void ABonfire::BeginPlay()
{
	Super::BeginPlay();

	FlameMaterial = Flame->CreateDynamicMaterialInstance(0);
	SetFireIntensity(GetBaseIntensity());

	// the player remembers where the hub bonfire is (it may stream out later)
	if (IsMainBonfire())
	{
		if (AOss_TermProjectCharacter* Player = Cast<AOss_TermProjectCharacter>(UGameplayStatics::GetPlayerPawn(this, 0)))
		{
			Player->RegisterMainBonfire(this);
		}
	}
}

bool ABonfire::IsMainBonfire() const
{
	static const FName MainName(TEXT("Bonfire_Main"));
	if (ActorHasTag(MainName))
	{
		return true;
	}
#if WITH_EDITOR
	if (GetActorLabel() == MainName.ToString())
	{
		return true;
	}
#endif
	return false;
}

ABonfire* ABonfire::FindMainBonfire(const UWorld* World)
{
	if (World)
	{
		for (TActorIterator<ABonfire> It(World); It; ++It)
		{
			if (It->IsMainBonfire())
			{
				return *It;
			}
		}
	}
	return nullptr;
}

void ABonfire::SetFireIntensity(float LightIntensity)
{
	Glow->SetIntensity(LightIntensity);
	if (FlameMaterial)
	{
		// the flame brightens less than the light (sqrt: x1.4 when focused, x2.6 at the rest flash)
		const float Ratio = GlowIntensity > 0.f ? LightIntensity / GlowIntensity : 1.f;
		FlameMaterial->SetScalarParameterValue(TEXT("Glow"), FlameGlow * FMath::Sqrt(FMath::Max(Ratio, 0.f)));
	}
}

bool ABonfire::CanInteract_Implementation(AActor* Interactor) const
{
	const AOss_TermProjectCharacter* Player = Cast<AOss_TermProjectCharacter>(Interactor);
	return Player && Player->GetStats() && !Player->GetStats()->IsDead();
}

void ABonfire::Interact_Implementation(AActor* Interactor)
{
	AOss_TermProjectCharacter* Player = Cast<AOss_TermProjectCharacter>(Interactor);
	if (!Player || !Player->GetStats() || Player->GetStats()->IsDead())
	{
		return;
	}

	// already sitting: stand up
	if (Player->IsResting())
	{
		Player->StopResting();
		return;
	}

	// sit: full health, stamina and potions, enemies reset, this becomes the respawn point
	Player->StartResting(this);

	// brief light flash as feedback
	FlashStartTime = GetWorld()->GetTimeSeconds();
	SetFireIntensity(RestFlashIntensity);
	GetWorldTimerManager().SetTimer(FlashTimer, this, &ABonfire::UpdateFlash, 1.f / 60.f, true);

	if (GEngine)
	{
		GEngine->AddOnScreenDebugMessage(-1, 2.f, Color.ToFColor(true), TEXT("Rested at bonfire"));
	}
	UE_LOG(LogOss_TermProject, Log, TEXT("'%s' rested at '%s'"), *GetNameSafe(Player), *GetNameSafe(this));

	OnRested(Interactor);
}

void ABonfire::UpdateFlash()
{
	const float Alpha = FMath::Clamp((GetWorld()->GetTimeSeconds() - FlashStartTime) / RestFlashDuration, 0.f, 1.f);
	SetFireIntensity(FMath::Lerp(RestFlashIntensity, GetBaseIntensity(), Alpha));
	if (Alpha >= 1.f)
	{
		GetWorldTimerManager().ClearTimer(FlashTimer);
	}
}

FText ABonfire::GetInteractionPrompt_Implementation() const
{
	const AOss_TermProjectCharacter* Player = Cast<AOss_TermProjectCharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	return (Player && Player->IsResting())
		? NSLOCTEXT("Bonfire", "LeavePrompt", "Stand up")
		: NSLOCTEXT("Bonfire", "RestPrompt", "Rest");
}

FTransform ABonfire::GetRespawnTransform() const
{
	const FVector Forward = FVector(GetActorForwardVector().X, GetActorForwardVector().Y, 0.f).GetSafeNormal();
	// capsule center height above the floor (default character capsule half height)
	const FVector Location = GetActorLocation() + Forward * (RespawnDistance + FMath::Max(Size.X, Size.Y) * 0.5f) + FVector(0.f, 0.f, 100.f);
	return FTransform((-Forward).Rotation(), Location);
}

void ABonfire::SetInteractionFocus_Implementation(AActor* Interactor, bool bInFocused)
{
	bFocused = bInFocused;
	if (!GetWorldTimerManager().IsTimerActive(FlashTimer))
	{
		SetFireIntensity(GetBaseIntensity());
	}
}
