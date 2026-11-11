// Bonfire (rest point): interact (E) to restore health, stamina and potions. Temporary look: a glowing box

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

ABonfire::ABonfire()
{
	PrimaryActorTick.bCanEverTick = false;

	// origin on the floor; the box sits on top of it
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));

	Body = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Body"));
	Body->SetupAttachment(RootComponent);
	Body->SetCollisionProfileName(UCollisionProfile::BlockAll_ProfileName);
	Body->SetCollisionResponseToChannel(ECC_Camera, ECR_Ignore);

	static ConstructorHelpers::FObjectFinder<UStaticMesh> CubeMesh(TEXT("/Engine/BasicShapes/Cube.Cube"));
	if (CubeMesh.Succeeded())
	{
		Body->SetStaticMesh(CubeMesh.Object);
	}

	Glow = CreateDefaultSubobject<UPointLightComponent>(TEXT("Glow"));
	Glow->SetupAttachment(RootComponent);
	Glow->SetAttenuationRadius(600.f);
	Glow->SetCastShadows(false);
}

void ABonfire::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);

	// engine cube is 100cm and centered: scale it and lift it so the actor's origin sits on the floor
	Body->SetRelativeScale3D(Size / 100.f);
	Body->SetRelativeLocation(FVector(0.f, 0.f, Size.Z * 0.5f));
	Glow->SetRelativeLocation(FVector(0.f, 0.f, Size.Z + 60.f));
	Glow->SetLightColor(Color);
	Glow->SetIntensity(GlowIntensity);
}

void ABonfire::BeginPlay()
{
	Super::BeginPlay();

	BodyMaterial = Body->CreateDynamicMaterialInstance(0);
	if (BodyMaterial)
	{
		BodyMaterial->SetVectorParameterValue(TEXT("Color"), Color);
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
	Glow->SetIntensity(RestFlashIntensity);
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
	Glow->SetIntensity(FMath::Lerp(RestFlashIntensity, GetBaseIntensity(), Alpha));
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
		Glow->SetIntensity(GetBaseIntensity());
	}
}
