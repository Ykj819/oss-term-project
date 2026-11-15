// Boss phase-2 weather: a view effect (unbound post process, optional white frost border on screen) plus falling
// particles (instanced engine shapes around the player). Snow for the wolf, rain for the fishman.

#include "BossWeatherComponent.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "UObject/UObjectIterator.h"
#include "Components/PostProcessComponent.h"
#include "Engine/GameViewportClient.h"
#include "Engine/StaticMesh.h"
#include "Engine/Texture2D.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/Material.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "Styling/SlateBrush.h"
#include "Widgets/Images/SImage.h"

namespace
{
	constexpr int32 FrostTextureSize = 256;
}

UBossWeatherComponent::UBossWeatherComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.TickGroup = TG_PostPhysics;
}

void UBossWeatherComponent::BeginPlay()
{
	Super::BeginPlay();
	SetupPostProcess();
	SetupParticles();
}

void UBossWeatherComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	ShowFrost(false);
	Super::EndPlay(EndPlayReason);
}

// ---------------------------------------------------------------- setup

void UBossWeatherComponent::SetupPostProcess()
{
	AActor* Owner = GetOwner();
	PostProcess = NewObject<UPostProcessComponent>(Owner, TEXT("WeatherPostProcess"));
	PostProcess->SetupAttachment(Owner->GetRootComponent());
	PostProcess->bUnbound = true;
	PostProcess->BlendWeight = 0.f;
	PostProcess->RegisterComponent();

	FPostProcessSettings& PP = PostProcess->Settings;
	PP.bOverride_VignetteIntensity = true;
	PP.bOverride_SceneColorTint = true;
	PP.bOverride_ColorSaturation = true;
	PP.bOverride_ColorContrast = true;
	if (Weather == EBossWeather::Snow)
	{
		// cold and pale; the white frost border is drawn on top of the screen
		PP.VignetteIntensity = 0.3f;
		PP.SceneColorTint = FLinearColor(0.9f, 0.96f, 1.08f);
		PP.ColorSaturation = FVector4(0.7f, 0.7f, 0.7f, 1.f);
		PP.ColorContrast = FVector4(0.92f, 0.92f, 0.92f, 1.f);
		PP.bOverride_AutoExposureBias = true;
		PP.AutoExposureBias = 0.35f;
	}
	else
	{
		// wet and grey-blue but still bright (the tree's storm is darker: strong vignette, warm tint, blur)
		PP.VignetteIntensity = 0.55f;
		PP.SceneColorTint = FLinearColor(0.88f, 0.94f, 1.03f);
		PP.ColorSaturation = FVector4(0.82f, 0.82f, 0.82f, 1.f);
		PP.ColorContrast = FVector4(0.95f, 0.95f, 0.95f, 1.f);
	}
	if (VignetteIntensity >= 0.f)
	{
		PP.VignetteIntensity = VignetteIntensity;
	}
}

void UBossWeatherComponent::SetupParticles()
{
	AActor* Owner = GetOwner();
	Particles = NewObject<UInstancedStaticMeshComponent>(Owner, TEXT("WeatherParticles"));
	Particles->SetupAttachment(Owner->GetRootComponent());
	Particles->SetUsingAbsoluteLocation(true);
	Particles->SetUsingAbsoluteRotation(true);
	Particles->SetUsingAbsoluteScale(true);
	Particles->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Particles->SetGenerateOverlapEvents(false);
	Particles->SetCastShadow(false);
	Particles->SetCanEverAffectNavigation(false);

	const bool bSnow = Weather == EBossWeather::Snow;
	if (UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, bSnow ? TEXT("/Engine/BasicShapes/Sphere.Sphere") : TEXT("/Engine/BasicShapes/Cube.Cube")))
	{
		Particles->SetStaticMesh(Mesh);
	}
	// Project material (Tools/create_weather_material.py): unlit + translucent + allowed on instanced meshes.
	// The engine debug materials can't be used here: they lack the instanced-mesh usage flag and are read-only,
	// so UE silently drew the grey default material instead (the "dark snow").
	UMaterialInterface* WeatherMat = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/Effects/M_WeatherParticle.M_WeatherParticle"));
	const bool bUnlit = WeatherMat != nullptr;
	if (bUnlit)
	{
		Particles->SetMaterial(0, WeatherMat);
	}
	else
	{
		// fallback: the shapes' own lit material (works on instanced meshes, but shaded)
		UE_LOG(LogTemp, Warning, TEXT("BossWeather: /Game/Effects/M_WeatherParticle missing - run Tools/create_weather_material.py. Using the lit basic material."));
	}
	Particles->RegisterComponent();
	Particles->SetWorldTransform(FTransform::Identity);
	Particles->SetVisibility(false);

	if (UMaterialInstanceDynamic* MID = Particles->CreateDynamicMaterialInstance(0))
	{
		// unlit particles must glow about as bright as a white surface in this level's light, or auto exposure makes them grey:
		// white Lambert surface luminance ~ sun lux / pi (+ some sky light)
		float SunLux = 0.f;
		for (TObjectIterator<UDirectionalLightComponent> It; It; ++It)
		{
			if (It->GetWorld() == GetWorld() && It->IsVisible())
			{
				SunLux = FMath::Max(SunLux, It->Intensity);
			}
		}
		if (SunLux <= 0.f)
		{
			SunLux = 10.f;	// UE default sun
		}
		const float Paper = bUnlit ? FMath::Max(1.f, 1.3f * SunLux / PI) : 1.f;
		if (bSnow)
		{
			const float White = SnowBrightness * 2.5f * Paper;
			MID->SetVectorParameterValue(TEXT("Color"), FLinearColor(White, White, White, 0.95f));
			UE_LOG(LogTemp, Log, TEXT("BossWeather snow: sun %.1f lux -> flake brightness %.2f (%s)"), SunLux, White, *GetNameSafe(MID->Parent));
		}
		else
		{
			const float B = 0.9f * Paper;
			MID->SetVectorParameterValue(TEXT("Color"), FLinearColor(0.80f * B, 0.87f * B, 1.0f * B, 0.30f));
		}
	}
	else
	{
		UE_LOG(LogTemp, Warning, TEXT("BossWeather: no material instance on the particles (material %s)"), *GetNameSafe(Particles->GetMaterial(0)));
	}
}

// ---------------------------------------------------------------- on / off

void UBossWeatherComponent::SetWeatherActive(bool bActive, bool bInstant)
{
	if (bActive && !bWeatherOn && Particles)
	{
		// fill the whole area at once (they fade in by growing)
		const FVector Center = AreaCenter();
		Drops.SetNum(ParticleCount);
		TArray<FTransform> Transforms;
		Transforms.Reserve(Drops.Num());
		for (FDrop& Drop : Drops)
		{
			RespawnDrop(Drop, Center, true);
			Transforms.Add(FTransform(FQuat::Identity, Drop.Position, FVector(0.001f)));
		}
		Particles->ClearInstances();
		Particles->AddInstances(Transforms, false, true);
		Particles->SetVisibility(true);
	}
	bWeatherOn = bActive;

	if (bActive && bFrostBorder)
	{
		ShowFrost(true);
	}
	if (bInstant)
	{
		Weight = bActive ? 1.f : 0.f;
		if (!bActive)
		{
			Drops.Reset();
			if (Particles)
			{
				Particles->ClearInstances();
				Particles->SetVisibility(false);
			}
			if (PostProcess)
			{
				PostProcess->BlendWeight = 0.f;
			}
			ShowFrost(false);
		}
	}
}

FVector UBossWeatherComponent::AreaCenter() const
{
	const APawn* Player = UGameplayStatics::GetPlayerPawn(this, 0);
	return Player ? Player->GetActorLocation() : GetOwner()->GetActorLocation();
}

void UBossWeatherComponent::RespawnDrop(FDrop& Drop, const FVector& Center, bool bAnywhere) const
{
	const FVector2D Disc = FMath::RandPointInCircle(AreaRadius);
	const float Height = bAnywhere ? FMath::FRandRange(-200.f, AreaHeight) : FMath::FRandRange(AreaHeight * 0.85f, AreaHeight);
	Drop.Position = Center + FVector(Disc.X, Disc.Y, Height);
	Drop.Phase = FMath::FRandRange(0.f, 2.f * PI);
	if (Weather == EBossWeather::Snow)
	{
		Drop.Velocity = FVector(Wind.X, Wind.Y, -FMath::FRandRange(110.f, 190.f));
		Drop.Size = FMath::FRandRange(0.05f, 0.09f);		// 5-9 cm flakes
	}
	else
	{
		Drop.Velocity = FVector(Wind.X, Wind.Y, -FMath::FRandRange(1900.f, 2500.f));
		Drop.Size = FMath::FRandRange(0.45f, 0.75f);		// 45-75 cm streaks
	}
}

// ---------------------------------------------------------------- per frame

void UBossWeatherComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);

	const float Target = bWeatherOn ? 1.f : 0.f;
	if (Weight == Target && !bWeatherOn)
	{
		return;		// idle
	}
	Weight = FMath::FInterpConstantTo(Weight, Target, DeltaTime, 1.f / FMath::Max(FadeTime, 0.1f));

	if (PostProcess)
	{
		PostProcess->BlendWeight = Weight * Intensity;
	}
	if (FrostImage.IsValid())
	{
		FrostImage->SetColorAndOpacity(FLinearColor(1.f, 1.f, 1.f, Weight * FrostBorderOpacity));
	}

	if (Weight <= 0.f && !bWeatherOn)
	{
		Drops.Reset();
		if (Particles)
		{
			Particles->ClearInstances();
			Particles->SetVisibility(false);
		}
		ShowFrost(false);
		return;
	}
	UpdateParticles(DeltaTime);
}

void UBossWeatherComponent::UpdateParticles(float DeltaTime)
{
	if (!Particles || Drops.Num() == 0 || Particles->GetInstanceCount() != Drops.Num())
	{
		return;
	}

	const FVector Center = AreaCenter();
	const float Time = GetWorld()->GetTimeSeconds();
	const float Grow = FMath::Clamp(Weight * 1.5f, 0.f, 1.f);
	const bool bSnow = Weather == EBossWeather::Snow;

	TArray<FTransform> Transforms;
	Transforms.SetNum(Drops.Num());
	for (int32 i = 0; i < Drops.Num(); ++i)
	{
		FDrop& Drop = Drops[i];
		FVector Move = Drop.Velocity;
		if (bSnow)
		{
			// flakes flutter sideways
			Move += FVector(FMath::Sin(Time * 0.9f + Drop.Phase) * 45.f, FMath::Cos(Time * 0.7f + Drop.Phase * 1.3f) * 45.f, 0.f);
		}
		Drop.Position += Move * DeltaTime;

		const FVector Offset = Drop.Position - Center;
		if (Offset.Z < -260.f || FVector2D(Offset.X, Offset.Y).SizeSquared() > FMath::Square(AreaRadius))
		{
			RespawnDrop(Drop, Center, false);
		}

		if (bSnow)
		{
			Transforms[i] = FTransform(FQuat::Identity, Drop.Position, FVector(Drop.Size * Grow));
		}
		else
		{
			// thin streak along its fall direction (engine cube is 100cm)
			const FQuat Along = FRotationMatrix::MakeFromZ(Drop.Velocity.GetSafeNormal()).ToQuat();
			Transforms[i] = FTransform(Along, Drop.Position, FVector(0.012f, 0.012f, Drop.Size) * Grow);
		}
	}
	Particles->BatchUpdateInstancesTransforms(0, Transforms, true, true, true);
}

// ---------------------------------------------------------------- frost border (Slate image over the viewport)

void UBossWeatherComponent::BuildFrostTexture()
{
	if (FrostTexture)
	{
		return;
	}

	// white, opaque at the screen edges (rounded-square falloff) with a frosty speckle, clear in the middle
	const int32 N = FrostTextureSize;
	TArray<FColor> Pixels;
	Pixels.SetNumUninitialized(N * N);
	FRandomStream Rand(4242);
	for (int32 y = 0; y < N; ++y)
	{
		for (int32 x = 0; x < N; ++x)
		{
			const float U = (x + 0.5f) / N * 2.f - 1.f;
			const float V = (y + 0.5f) / N * 2.f - 1.f;
			const float Edge = FMath::Pow(FMath::Pow(FMath::Abs(U), 4.f) + FMath::Pow(FMath::Abs(V), 4.f), 0.25f);
			float A = FMath::SmoothStep(0.62f, 1.02f, Edge);
			A = FMath::Pow(A, 1.3f) * (0.72f + 0.28f * Rand.FRand());
			Pixels[y * N + x] = FColor(236, 246, 255, (uint8)FMath::Clamp(FMath::RoundToInt(A * 255.f), 0, 255));	// slightly cold white (FColor args are R,G,B,A)
		}
	}

	FrostTexture = UTexture2D::CreateTransient(N, N, PF_B8G8R8A8);
	if (!FrostTexture)
	{
		return;
	}
	FrostTexture->Filter = TF_Bilinear;
	FTexture2DMipMap& Mip = FrostTexture->GetPlatformData()->Mips[0];
	void* Data = Mip.BulkData.Lock(LOCK_READ_WRITE);
	FMemory::Memcpy(Data, Pixels.GetData(), Pixels.Num() * sizeof(FColor));
	Mip.BulkData.Unlock();
	FrostTexture->UpdateResource();
}

void UBossWeatherComponent::ShowFrost(bool bShow)
{
	UGameViewportClient* Viewport = GetWorld() ? GetWorld()->GetGameViewport() : nullptr;
	if (bShow)
	{
		if (FrostImage.IsValid() || !Viewport)
		{
			return;
		}
		BuildFrostTexture();
		if (!FrostTexture)
		{
			return;
		}
		FrostBrush = MakeShared<FSlateBrush>();
		FrostBrush->SetResourceObject(FrostTexture);
		FrostBrush->ImageSize = FVector2D(FrostTextureSize, FrostTextureSize);
		FrostBrush->DrawAs = ESlateBrushDrawType::Image;
		FrostImage = SNew(SImage)
			.Image(FrostBrush.Get())
			.ColorAndOpacity(FLinearColor(1.f, 1.f, 1.f, 0.f))
			.Visibility(EVisibility::HitTestInvisible);
		Viewport->AddViewportWidgetContent(FrostImage.ToSharedRef(), 5);	// under the HUD (10)
	}
	else if (FrostImage.IsValid())
	{
		if (Viewport)
		{
			Viewport->RemoveViewportWidgetContent(FrostImage.ToSharedRef());
		}
		FrostImage.Reset();
		FrostBrush.Reset();
	}
}
